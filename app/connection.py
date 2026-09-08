import os
from pathlib import Path

from config import Config
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

_engine = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _build_connection_string() -> str:
    """
    Return the SQLAlchemy DSN.

    A full ``DATABASE_URL`` wins when present (managed providers hand one out
    ready-made); otherwise the DSN is composed from the individual ``DB_*``
    settings, which is how the Docker Compose stack supplies them.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    return "mysql+pymysql://{}:{}@{}:{}/{}".format(
        Config.DB_USER, Config.DB_PASSWORD, Config.DB_URI, Config.DB_PORT, Config.DB_NAME
    )


def _build_connect_args() -> dict:
    """
    Return driver-level TLS options.

    Managed databases such as Aiven refuse plaintext connections. ``DB_SSL_CA``
    points at the provider's CA certificate and gives a verified connection;
    ``DB_SSL`` alone falls back to encryption without certificate verification.
    Neither set means a local, unencrypted connection.
    """
    ca_path = os.getenv("DB_SSL_CA")
    if ca_path:
        ca = Path(ca_path)
        if not ca.is_absolute():
            ca = PROJECT_ROOT / ca
        return {"ssl": {"ca": str(ca)}}

    if os.getenv("DB_SSL", "").lower() in ("1", "true", "require"):
        return {"ssl": {}}

    return {}


def _is_serverless() -> bool:
    """True when running as a Vercel function rather than a long-lived server."""
    return bool(os.getenv("VERCEL"))


def get_db():
    global _engine
    if _engine is None:
        if _is_serverless():
            # Every warm serverless instance would otherwise keep its own pool
            # of idle connections open, and enough of them will exhaust the
            # connection limit of a small managed database. Take a connection
            # per request and hand it back immediately.
            pool_options = {"poolclass": NullPool}
        else:
            pool_options = {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_recycle": 3600,
            }

        _engine = create_engine(
            _build_connection_string(),
            connect_args=_build_connect_args(),
            pool_pre_ping=True,
            **pool_options,
        )
    return _engine
