"""Gunicorn entrypoint: gunicorn -w 1 --threads 4 src.dashboard.wsgi:server

Import-time side effects (table creation, collector threads) live here so that
importing src.dashboard.app stays side-effect-free — CI's verify job smoke-tests
that import on a runner with no database.

Keep -w 1: each extra worker would load its own copy of the sentiment model and
duplicate the background collectors.
"""

from src.dashboard.app import app, init_app

init_app()
server = app.server
