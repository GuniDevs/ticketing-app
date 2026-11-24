from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..auth import roles_required
from ..services import user_service
from ._util import json_body

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.post("")
@roles_required("admin")
def create_user():
    body = json_body()
    user = user_service.create_user(
        body.get("email"), body.get("name"), body.get("password"), body.get("role", "customer")
    )
    return jsonify(user.public()), 201


@bp.get("")
@roles_required("agent", "admin")
def list_users():
    users = user_service.list_users(request.args.get("role") or None)
    return jsonify({"items": [user.public() for user in users]})


@bp.get("/<int:user_id>")
@roles_required("agent", "admin")
def get_user(user_id: int):
    return jsonify(user_service.get_user(user_id).public())
