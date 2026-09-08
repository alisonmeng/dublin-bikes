import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""
    # Signs the session cookie. Sessions are the only authentication mechanism,
    # so a missing or guessable value means anyone can forge a login; create_app
    # refuses to start without it outside DEBUG/TESTING.
    SECRET_KEY = os.getenv("SECRET_KEY")

    BIKE_KEY = os.getenv("BIKE_KEY")
    WEATHER_KEY = os.getenv("WEATHER_KEY")
    MAP_KEY = os.getenv("MAP_KEY")
    MAP_ID  = os.getenv("MAP_ID")

    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_URI = os.getenv("DB_URI")

    # General
    DEBUG = False
    TESTING = False

    # Cookie
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):

    DEBUG = False

    # Production is served over HTTPS (Vercel, or Nginx in the Docker stack),
    # so the session cookie must never travel over a plaintext connection.
    SESSION_COOKIE_SECURE = True