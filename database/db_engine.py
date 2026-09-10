"""
Shared database connection for the scripts in this directory.

These scripts run outside the web application - from a laptop, or from CI - so
they cannot use app/connection.py: importing anything from the `app` package
executes app/__init__.py, which builds the Flask app and loads both prediction
models. This keeps the same connection rules without that cost.

Managed providers such as Aiven refuse plaintext connections, so TLS settings
matter here as much as they do in the app.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_connection_string() -> str:
    """Return the SQLAlchemy DSN, preferring a full DATABASE_URL when provided."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    missing = [
        name for name in ("DB_USER", "DB_PASSWORD", "DB_URI", "DB_PORT", "DB_NAME")
        if not os.getenv(name)
    ]
    if missing:
        raise SystemExit(
            f"Missing database settings: {', '.join(missing)}.\n"
            "Set them in a .env file in the project root, or set DATABASE_URL.\n"
            "Note DB_URI is the database *hostname*, not a full URI."
        )

    return "mysql+pymysql://{}:{}@{}:{}/{}".format(
        os.getenv("DB_USER"), os.getenv("DB_PASSWORD"),
        os.getenv("DB_URI"), os.getenv("DB_PORT"), os.getenv("DB_NAME"),
    )


def build_connect_args() -> dict:
    """Return driver-level TLS options, matching app/connection.py."""
    ca_path = os.getenv("DB_SSL_CA")
    if ca_path:
        ca = Path(ca_path)
        if not ca.is_absolute():
            ca = PROJECT_ROOT / ca
        if not ca.exists():
            raise SystemExit(f"DB_SSL_CA points at {ca}, which does not exist.")
        return {"ssl": {"ca": str(ca)}}

    if os.getenv("DB_SSL", "").lower() in ("1", "true", "require"):
        return {"ssl": {}}

    return {}


def build_engine(echo: bool = False):
    """Create an engine configured for whichever database is in the environment."""
    return create_engine(
        build_connection_string(),
        connect_args=build_connect_args(),
        pool_pre_ping=True,
        echo=echo,
    )
