"""
Smoke tests for a running deployment.

These hit a real server over HTTP rather than a Flask test client, so they
catch the class of problem that unit tests cannot: environment variables that
never arrived, a database that is unreachable or un-seeded, static files that
are not served, and templates rendered with empty configuration.

Run against production:

    python -m unittest discover -s tests/smoke -t . -v

Or against any other deployment:

    SMOKE_BASE_URL=https://dublin-bikes-git-main-....vercel.app \
        python -m unittest discover -s tests/smoke -t . -v

One thing these cannot check: whether Google accepts the Maps API key. That
decision happens in the browser, against the page's Referer, so a server-side
request cannot observe it -- a key rejected with RefererNotAllowedMapError
looks identical from here to one that works. test_home_page_supplies_map_config
asserts what is checkable, namely that a non-empty key and map id actually
reach the page; the browser console is the only place the rest shows up.
"""
import os
import unittest
from datetime import datetime, timedelta

import requests

BASE_URL = os.getenv("SMOKE_BASE_URL", "https://dublin-bikes.vercel.app").rstrip("/")

# Generous: a cold serverless start loads both models before serving.
TIMEOUT = 60


def get(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{BASE_URL}{path}", timeout=TIMEOUT, **kwargs)


class TestHealth(unittest.TestCase):
    """The health endpoint summarises configuration and database state."""

    def test_healthz_reports_a_healthy_deployment(self):
        """
        /healthz must return 200. On failure the body names the specific
        problem -- missing settings, a malformed DB_URI, an unreachable
        database or missing tables -- so it is included in the assertion
        message rather than left in the logs.
        """
        response = get("/healthz")
        self.assertEqual(
            response.status_code, 200,
            f"deployment is degraded: {response.text[:800]}"
        )
        self.assertEqual(response.json()["status"], "ok")


class TestPages(unittest.TestCase):
    """Every page a visitor can reach without logging in."""

    def test_home_page_renders(self):
        response = get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="map"', response.text)

    def test_home_page_supplies_map_config(self):
        """
        The template interpolates MAP_KEY and MAP_ID into the page. If either
        is unset the page still returns 200, and the map silently fails to
        load -- so assert they are actually populated.
        """
        response = get("/")
        self.assertNotIn(
            "maps/api/js?key=&", response.text,
            "MAP_KEY is empty - the Google Maps script will fail to authenticate"
        )
        self.assertNotIn(
            'data-map-id=""', response.text,
            "MAP_ID is empty - Advanced Markers will not render"
        )

    def test_static_files_are_served(self):
        response = get("/static/css/styles.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response.headers.get("Content-Type", ""))

    def test_content_pages_render(self):
        for path in ("/safety", "/faq"):
            with self.subTest(path=path):
                self.assertEqual(get(path).status_code, 200)

    def test_login_page_renders(self):
        self.assertEqual(get("/auth/login").status_code, 200)

    def test_account_requires_login(self):
        """An anonymous visitor is redirected to the login page, not shown an error."""
        response = get("/account", allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])


class TestLiveApis(unittest.TestCase):
    """Endpoints backed by third-party APIs."""

    def test_bikes_returns_live_stations(self):
        response = get("/api/bikes")
        self.assertEqual(response.status_code, 200)
        stations = response.json()
        self.assertGreater(len(stations), 0, "JCDecaux returned no stations")
        self.assertIn("available_bikes", stations[0])

    def test_weather_returns_a_temperature(self):
        response = get("/api/weather")
        self.assertEqual(response.status_code, 200)
        self.assertIn("temp", response.json().get("main", {}))


class TestDatabase(unittest.TestCase):
    """Endpoints backed by the database."""

    def test_stations_are_served_from_the_database(self):
        """
        The map calls this on load, so a failure here leaves the map empty
        even when Google Maps itself is working.
        """
        response = get("/db/stations")
        self.assertEqual(
            response.status_code, 200,
            f"/db/stations failed - check /healthz. Body: {response.text[:300]}"
        )
        stations = response.json()["stations"]
        self.assertGreater(
            len(stations), 0,
            "the station table is empty - run database/bulk_bike_insert.py"
        )
        self.assertIn("bike_stands", stations[0])


class TestPredictions(unittest.TestCase):
    """The ML routes, which need both the models and the station table."""

    def _forecast(self, path: str, series_key: str):
        tomorrow = datetime.now() + timedelta(days=1)
        response = get(
            f"{path}?station_id=42"
            f"&date={tomorrow:%Y-%m-%d}&time={tomorrow:%H:00:00}"
        )
        self.assertEqual(response.status_code, 200, response.text[:300])

        chart = response.json()["chart_data"]
        self.assertEqual(len(chart["labels"]), 24)
        self.assertEqual(len(chart[series_key]), 24)
        for value in chart[series_key]:
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)

    def test_bike_forecast(self):
        self._forecast("/predict/bike/24h", "data_available_bikes")

    def test_stand_forecast(self):
        self._forecast("/predict/stand/24h", "data_empty_stands")


if __name__ == "__main__":
    unittest.main()
