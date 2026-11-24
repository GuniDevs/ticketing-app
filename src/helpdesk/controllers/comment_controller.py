from __future__ import annotations

from flask import Blueprint, g, jsonify

from ..auth import login_required
from ..services import comment_service
from ._util import json_body

bp = Blueprint("comments", __name__, url_prefix="/api/tickets/<int:ticket_id>/comments")


@bp.get("")
@login_required
def list_comments(ticket_id: int):
    comments = comment_service.list_comments(g.user, ticket_id)
    return jsonify({"items": [comment.to_dict() for comment in comments]})


@bp.post("")
@login_required
def add_comment(ticket_id: int):
    body = json_body()
    comment = comment_service.add_comment(g.user, ticket_id, body.get("body"), body.get("internal", False))
    return jsonify(comment.to_dict()), 201
