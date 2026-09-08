"""
This file should ONLY contain "create_app" function
"""
import os

from flask import Flask
from flask_cors import CORS
from config import Config
from datetime import timedelta
from .routes.machine_learning import ml_bp


def _resolve_secret_key(app) -> str:
    """
    Return the key used to sign session cookies.

    Refuses to fall back to a placeholder outside DEBUG/TESTING: the session
    cookie is the only thing distinguishing one logged-in user from another, so
    a key an attacker can read is the same as no authentication at all.
    """
    secret_key = app.config.get('SECRET_KEY') or os.environ.get('SECRET_KEY')
    if secret_key:
        return secret_key

    if app.config.get('DEBUG') or app.config.get('TESTING'):
        return 'dev-only-insecure-key'

    raise RuntimeError(
        'SECRET_KEY is not set. Set it in the environment before starting the '
        'app in production - without it, session cookies can be forged.'
    )


def create_app(config_class=Config):
    app = Flask(__name__)

    # Import blueprints and cache AFTER creating app but BEFORE using them
    from .routes.main import main_bp, cache
    from .routes.auth import auth_bp, load_logged_in_user

    app.config.from_object(config_class)
    CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:63342", "http://localhost:63342"]}},
         supports_credentials=True)

    # cache
    cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache'})

    app.secret_key = _resolve_secret_key(app)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    # Make g.user available on ALL routes (not just /auth/*)
    app.before_request(load_logged_in_user)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(ml_bp, url_prefix='/predict')

    return app
