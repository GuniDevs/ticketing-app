from __future__ import annotations

from flask import Blueprint, g, jsonify

from ..auth import issue_token, login_required
from ..services import user_service
from ._util import json_body

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    body = json_body()
    user = user_service.register(body.get("email"), body.get("name"), body.get("password"))
    return jsonify(user.public()), 201


@bp.post("/login")
def login():
    body = json_body()
    user = user_service.authenticate(body.get("email"), body.get("password"))
    return jsonify({"token": issue_token(user.id, user.role), "user": user.public()})


@bp.get("/me")
@login_required
def me():
    return jsonify(g.user.public())
