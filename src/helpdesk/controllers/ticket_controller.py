from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..auth import login_required, roles_required
from ..services import ticket_service
from ._util import int_arg, json_body, max_per_page, optional_int_arg

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")


@bp.post("")
@login_required
def create_ticket():
    body = json_body()
    ticket = ticket_service.create_ticket(g.user, body.get("title"), body.get("description"), body.get("priority"))
    return jsonify(ticket.to_dict()), 201


@bp.get("")
@login_required
def list_tickets():
    result = ticket_service.list_tickets(
        g.user,
        status=request.args.get("status") or None,
        priority=request.args.get("priority") or None,
        assignee_id=optional_int_arg("assignee_id"),
        text=(request.args.get("q") or "").strip() or None,
        page=int_arg("page", 1, minimum=1),
        per_page=int_arg("per_page", 20, minimum=1, maximum=max_per_page()),
    )
    return jsonify(result)


@bp.get("/<int:ticket_id>")
@login_required
def get_ticket(ticket_id: int):
    return jsonify(ticket_service.load_visible(g.user, ticket_id).to_dict())


@bp.patch("/<int:ticket_id>/status")
@login_required
def change_status(ticket_id: int):
    ticket = ticket_service.change_status(g.user, ticket_id, json_body().get("status"))
    return jsonify(ticket.to_dict())


@bp.post("/<int:ticket_id>/assign")
@roles_required("agent", "admin")
def assign(ticket_id: int):
    ticket = ticket_service.assign(g.user, ticket_id, json_body().get("agent_id"))
    return jsonify(ticket.to_dict())
