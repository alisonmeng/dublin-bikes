"""
Entrypoint for the Vercel Python runtime.

Vercel imports ``app`` from this module and serves it as a WSGI application.
The file is deliberately named ``main.py`` and not ``app.py``: a module named
``app`` at the repository root would shadow the ``app`` package it imports from.

``run.py`` remains the entrypoint for running the app locally.
"""
from dotenv import load_dotenv

# Must run before config is imported: Config reads os.getenv at class-body time.
load_dotenv()

from app import create_app
from config import ProductionConfig

app = create_app(ProductionConfig)


if __name__ == "__main__":
    app.run()
