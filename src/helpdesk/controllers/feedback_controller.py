from __future__ import annotations

from flask import Blueprint, g, jsonify

from ..auth import login_required, roles_required
from ..services import history_service, rating_service, ticket_service
from ._util import json_body

bp = Blueprint("feedback", __name__, url_prefix="/api/tickets/<int:ticket_id>")


@bp.get("/history")
@roles_required("agent", "admin")
def history(ticket_id: int):
    ticket = ticket_service.load_visible(g.user, ticket_id)
    return jsonify({"items": [event.to_dict() for event in history_service.history(ticket.id)]})


@bp.post("/rating")
@login_required
def rate(ticket_id: int):
    body = json_body()
    rating = rating_service.rate(g.user, ticket_id, body.get("score"), body.get("feedback"))
    return jsonify(rating.to_dict()), 201


@bp.get("/rating")
@login_required
def get_rating(ticket_id: int):
    return jsonify(rating_service.get_rating(g.user, ticket_id).to_dict())
