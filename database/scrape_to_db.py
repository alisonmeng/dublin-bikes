"""
Scheduled data collector.

One run refreshes the station list, appends a live availability sample for every
station, and appends the current Dublin weather reading. Intended to be driven
by .github/workflows/scrape.yml, but it is an ordinary script and can be run by
hand against any configured database.

Every write is an upsert keyed on the tables' primary keys -- (number,
last_update) for availability and dt for weather -- so overlapping schedules,
retries and manual runs cannot create duplicates or fail on them.

Connects via database/db_engine.py rather than app.connection: importing
anything from the `app` package executes app/__init__.py, which loads the
prediction blueprint and with it both models. There is no reason to pay for
that on a cron run that only talks to two APIs and a database.
"""
import os
import sys
from datetime import datetime, timezone

import requests
from sqlalchemy import text

from db_engine import build_engine

STATIONS_URL = "https://api.jcdecaux.com/vls/v1/stations"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
CONTRACT = "dublin"
REQUEST_TIMEOUT = 30


def fetch_stations() -> list:
    """Return the live JCDecaux payload for every Dublin station."""
    response = requests.get(
        STATIONS_URL,
        params={"apiKey": os.getenv("BIKE_KEY"), "contract": CONTRACT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def fetch_weather() -> dict:
    """Return the current OpenWeather reading for Dublin."""
    response = requests.get(
        WEATHER_URL,
        params={"appid": os.getenv("WEATHER_KEY"), "q": "dublin, ie", "units": "metric"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def upsert_stations(engine, stations: list) -> int:
    """Refresh the station table. Names and capacities do change occasionally."""
    sql = text("""
        INSERT INTO station (number, contract_name, name, address, bike_stands,
                             lat, lng, banking, bonus)
        VALUES (:number, :contract_name, :name, :address, :bike_stands,
                :lat, :lng, :banking, :bonus)
        ON DUPLICATE KEY UPDATE
            contract_name = VALUES(contract_name),
            name          = VALUES(name),
            address       = VALUES(address),
            bike_stands   = VALUES(bike_stands),
            lat           = VALUES(lat),
            lng           = VALUES(lng),
            banking       = VALUES(banking),
            bonus         = VALUES(bonus)
    """)

    rows = [{
        "number": s.get("number"),
        "contract_name": s.get("contract_name"),
        "name": s.get("name"),
        "address": s.get("address"),
        "bike_stands": s.get("bike_stands"),
        "lat": s.get("position", {}).get("lat"),
        "lng": s.get("position", {}).get("lng"),
        "banking": 1 if s.get("banking") else 0,
        "bonus": 1 if s.get("bonus") else 0,
    } for s in stations]

    with engine.begin() as conn:
        conn.execute(sql, rows)
    return len(rows)


def insert_availability(engine, stations: list) -> int:
    """
    Append one availability sample per station.

    JCDecaux stamps each station with its own last_update, which is part of the
    primary key, so a run that lands before a station has changed simply
    overwrites the identical row rather than failing.
    """
    sql = text("""
        INSERT INTO availability (number, available_bike_stands, available_bikes,
                                  status, last_update)
        VALUES (:number, :available_bike_stands, :available_bikes,
                :status, :last_update)
        ON DUPLICATE KEY UPDATE
            available_bike_stands = VALUES(available_bike_stands),
            available_bikes       = VALUES(available_bikes),
            status                = VALUES(status)
    """)

    rows = [{
        "number": s.get("number"),
        "available_bike_stands": s.get("available_bike_stands"),
        "available_bikes": s.get("available_bikes"),
        "status": s.get("status"),
        "last_update": s.get("last_update"),
    } for s in stations if s.get("last_update") is not None]

    with engine.begin() as conn:
        conn.execute(sql, rows)
    return len(rows)


def insert_weather(engine, weather: dict) -> int:
    """
    Append the current weather reading.

    OpenWeather's dt only advances every few minutes, so a run that catches an
    unchanged reading updates the existing row instead of duplicating it.
    """
    main = weather.get("main", {})
    sys_block = weather.get("sys", {})
    wind = weather.get("wind", {})

    row = {
        "dt": datetime.fromtimestamp(weather["dt"], tz=timezone.utc),
        "feels_like": main.get("feels_like"),
        "humidity": main.get("humidity"),
        "pressure": main.get("pressure"),
        "sunrise": datetime.fromtimestamp(sys_block["sunrise"], tz=timezone.utc)
                   if sys_block.get("sunrise") else None,
        "sunset": datetime.fromtimestamp(sys_block["sunset"], tz=timezone.utc)
                  if sys_block.get("sunset") else None,
        "temp": main.get("temp"),
        "weather_id": (weather.get("weather") or [{}])[0].get("id"),
        "wind_gust": wind.get("gust"),
        "wind_speed": wind.get("speed"),
        "rain_1h": weather.get("rain", {}).get("1h"),
        "snow_1h": weather.get("snow", {}).get("1h"),
    }

    sql = text("""
        INSERT INTO `current`
            (dt, feels_like, humidity, pressure, sunrise, sunset, `temp`,
             weather_id, wind_gust, wind_speed, rain_1h, snow_1h)
        VALUES
            (:dt, :feels_like, :humidity, :pressure, :sunrise, :sunset, :temp,
             :weather_id, :wind_gust, :wind_speed, :rain_1h, :snow_1h)
        ON DUPLICATE KEY UPDATE
            feels_like = VALUES(feels_like),
            humidity   = VALUES(humidity),
            pressure   = VALUES(pressure),
            `temp`     = VALUES(`temp`),
            weather_id = VALUES(weather_id),
            wind_gust  = VALUES(wind_gust),
            wind_speed = VALUES(wind_speed),
            rain_1h    = VALUES(rain_1h),
            snow_1h    = VALUES(snow_1h)
    """)

    with engine.begin() as conn:
        conn.execute(sql, row)
    return 1


def main() -> int:
    engine = build_engine()

    # The two sources fail independently: a JCDecaux outage should not cost us
    # the weather sample, and vice versa. Report at the end which ones failed.
    failures = []

    try:
        stations = fetch_stations()
        print(f"stations fetched: {len(stations)}")
        print(f"stations upserted: {upsert_stations(engine, stations)}")
        print(f"availability rows written: {insert_availability(engine, stations)}")
    except Exception as error:
        print(f"bike scrape failed: {error}", file=sys.stderr)
        failures.append("bikes")

    try:
        weather = fetch_weather()
        print(f"weather rows written: {insert_weather(engine, weather)}")
    except Exception as error:
        print(f"weather scrape failed: {error}", file=sys.stderr)
        failures.append("weather")

    if failures:
        print(f"run finished with failures: {', '.join(failures)}", file=sys.stderr)
        return 1

    print("run finished successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
