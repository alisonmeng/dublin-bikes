"""
Operational health check.

Exists so that a misconfigured deployment reports what is wrong in one HTTP
request, instead of surfacing as an opaque 500 that has to be traced through
the hosting platform's logs.

Nothing here returns a secret. Configuration is reported by name and by shape
only -- whether a value is present, and whether it looks malformed -- never its
contents.
"""
import os
import socket

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.connection import get_db

health_bp = Blueprint("health", __name__)

# Settings the application needs in production. DATABASE_URL is an accepted
# alternative to the five DB_* parts, so it is checked separately.
REQUIRED_SETTINGS = (
    "SECRET_KEY", "BIKE_KEY", "WEATHER_KEY", "MAP_KEY", "MAP_ID",
)
DATABASE_PARTS = ("DB_USER", "DB_PASSWORD", "DB_URI", "DB_PORT", "DB_NAME")


def _check_configuration() -> dict:
    """Report which expected settings arrived, by name only."""
    missing = [name for name in REQUIRED_SETTINGS if not os.getenv(name)]

    if os.getenv("DATABASE_URL"):
        database_config = "DATABASE_URL"
    else:
        database_config = "DB_* parts"
        missing += [name for name in DATABASE_PARTS if not os.getenv(name)]

    return {
        "ok": not missing,
        "database_config": database_config,
        "missing": sorted(missing),
    }


def _check_database_host() -> dict:
    """
    Flag the shapes of DB_URI that cannot resolve.

    DB_URI is a hostname, not a URI, despite the name. Pasting a provider's
    full connection string into it produces a DNS failure whose error message
    says nothing about the real mistake, so name the mistake here instead.
    """
    host = os.getenv("DB_URI")
    if not host:
        return {"set": False}

    problems = []
    if "://" in host:
        problems.append("contains a scheme - DB_URI takes a bare hostname, not a URL")
    if "@" in host:
        problems.append("contains credentials - put those in DB_USER / DB_PASSWORD")
    if ":" in host.split("://")[-1]:
        problems.append("contains a port - put that in DB_PORT")
    if host != host.strip():
        problems.append("has leading or trailing whitespace")
    if "/" in host.split("://")[-1]:
        problems.append("contains a path - put the database name in DB_NAME")

    return {"set": True, "looks_valid": not problems, "problems": problems}


def _check_dns() -> dict:
    """
    Resolve the database hostname on its own.

    Worth separating from the connection attempt: a name that does not resolve
    and a server that refuses a connection are different problems with
    different fixes, and the driver reports both as one opaque OperationalError.
    A hostname that returns NXDOMAIN usually means it was mistyped, or the
    managed service has been powered off or deleted.
    """
    host = os.getenv("DB_URI")
    if not host:
        return {"ok": False, "skipped": "DB_URI is not set"}

    try:
        socket.getaddrinfo(host, None)
        return {"ok": True, "resolves": True}
    except socket.gaierror as error:
        return {
            "ok": False,
            "resolves": False,
            "hint": "hostname does not resolve - check it against the provider "
                    "console, and that the service is running rather than "
                    "powered off or still being created",
            "error": str(error)[:200],
        }
    except OSError as error:
        # Some sandboxed runtimes surface resolution failures as a plain OSError
        # (EBUSY) rather than gaierror, which reads as a transient fault but is
        # not one.
        return {
            "ok": False,
            "resolves": False,
            "hint": "hostname could not be resolved by this runtime",
            "error": str(error)[:200],
        }


def _check_database() -> dict:
    """Try one trivial query, and report the failure rather than raising."""
    try:
        with get_db().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as error:
        # The exception type is far more diagnostic than the message here:
        # a resolution failure, a refused connection and a rejected password
        # are three very different problems.
        return {
            "ok": False,
            "error_type": type(error).__name__,
            "error": str(error)[:300],
        }


def _check_tables() -> dict:
    """Report which expected tables exist, so an un-seeded database is obvious."""
    expected = {"station", "availability", "current", "users", "user_favorites"}
    try:
        with get_db().connect() as conn:
            found = {row[0] for row in conn.execute(text("SHOW TABLES"))}
            station_rows = None
            if "station" in found:
                station_rows = conn.execute(
                    text("SELECT COUNT(*) FROM station")
                ).scalar()
        return {
            "ok": expected.issubset(found) and bool(station_rows),
            "missing": sorted(expected - found),
            "station_rows": station_rows,
        }
    except Exception as error:
        return {"ok": False, "error_type": type(error).__name__}


@health_bp.route("/healthz")
def healthz():
    """
    Report whether this deployment is correctly configured and connected.

    Returns 200 when everything needed to serve the site is working, and 503
    otherwise, so uptime checks and the smoke tests can rely on the status code
    alone while a human reads the body.
    """
    configuration = _check_configuration()
    dns = _check_dns()
    # No point dialling a name that does not resolve.
    database = _check_database() if dns["ok"] else {"ok": False, "skipped": True}

    checks = {
        "configuration": configuration,
        "database_host": _check_database_host(),
        "database_dns": dns,
        "database": database,
        # Only worth querying once a connection exists.
        "tables": _check_tables() if database["ok"] else {"ok": False, "skipped": True},
    }

    healthy = all(check.get("ok", True) for check in checks.values())
    return jsonify({"status": "ok" if healthy else "degraded", "checks": checks}), (
        200 if healthy else 503
    )
