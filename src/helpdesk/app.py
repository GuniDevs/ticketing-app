"""The app factory: settings, database, error handlers and the seven controllers."""

from __future__ import annotations

import os
import secrets
from typing import Any, Mapping

from flask import Flask, jsonify

from .controllers import ALL_BLUEPRINTS
from .db import close_db, init_db
from .errors import register_error_handlers


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("HELPDESK_DB", "helpdesk.db"),
        # Without HELPDESK_SECRET every start makes a new key, so tokens stop working after a restart.
        SECRET_KEY=os.environ.get("HELPDESK_SECRET") or secrets.token_hex(32),
        TOKEN_TTL_S=3600,
        MAX_PER_PAGE=100,
        CLOCK=None,
    )
    if config:
        app.config.update(config)

    register_error_handlers(app)
    app.teardown_appcontext(close_db)
    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    with app.app_context():
        init_db()
    return app
