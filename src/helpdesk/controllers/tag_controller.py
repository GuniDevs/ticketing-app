from __future__ import annotations

from flask import Blueprint, g, jsonify

from ..auth import login_required, roles_required
from ..services import tag_service
from ._util import json_body

bp = Blueprint("tags", __name__, url_prefix="/api")


@bp.get("/tickets/<int:ticket_id>/tags")
@login_required
def list_tags(ticket_id: int):
    return jsonify({"items": tag_service.list_for_ticket(g.user, ticket_id)})


@bp.post("/tickets/<int:ticket_id>/tags")
@login_required
def add_tag(ticket_id: int):
    return jsonify({"items": tag_service.add_tag(g.user, ticket_id, json_body().get("tag"))}), 201


@bp.delete("/tickets/<int:ticket_id>/tags/<tag>")
@roles_required("agent", "admin")
def remove_tag(ticket_id: int, tag: str):
    return jsonify({"items": tag_service.remove_tag(g.user, ticket_id, tag)})


@bp.get("/tags")
@roles_required("agent", "admin")
def usage():
    return jsonify({"items": tag_service.usage()})


@bp.get("/tags/<tag>/tickets")
@roles_required("agent", "admin")
def tickets_with(tag: str):
    return jsonify({"items": [ticket.to_dict() for ticket in tag_service.tickets_with(tag)]})
