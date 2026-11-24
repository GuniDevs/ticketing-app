from __future__ import annotations

from datetime import timedelta
from typing import Any

from .. import clock
from ..db import get_db
from ..errors import ApiError
from ..models import PRIORITIES, SLA_HOURS, STATUSES, TRANSITIONS, Ticket, User
from ..repositories import tickets as tickets_repo
from ..repositories import users as users_repo

TITLE_MIN, TITLE_MAX, DESCRIPTION_MAX = 3, 120, 5000


def _visible_to(user: User, ticket: Ticket) -> bool:
    """A customer sees only their own tickets; agents and admins see all of them."""
    return user.role != "customer" or ticket.requester_id == user.id


def load_visible(user: User, ticket_id: int) -> Ticket:
    """The ticket, or a 404. A customer asking for someone else's ticket gets the same 404 as for a missing one."""
    ticket = tickets_repo.get(get_db(), ticket_id)
    if ticket is None or not _visible_to(user, ticket):
        raise ApiError(404, "not_found", "ticket not found")
    return ticket


def pick_assignee() -> int | None:
    """The agent with the fewest open tickets (the lowest id wins a tie), or nobody if there are no agents."""
    db = get_db()
    agents = users_repo.list_all(db, "agent")
    if not agents:
        return None
    load = tickets_repo.active_counts_by_assignee(db)
    return min(agents, key=lambda agent: (load.get(agent.id, 0), agent.id)).id


def create_ticket(user: User, title: object, description: object, priority: object) -> Ticket:
    if not isinstance(title, str) or not isinstance(description, str):
        raise ApiError(400, "invalid_input", "title and description must be text")
    title = title.strip()
    if not TITLE_MIN <= len(title) <= TITLE_MAX:
        raise ApiError(400, "invalid_title", f"the title must be {TITLE_MIN} to {TITLE_MAX} characters")
    if not description.strip() or len(description) > DESCRIPTION_MAX:
        raise ApiError(400, "invalid_description", f"the description is required, up to {DESCRIPTION_MAX} characters")
    chosen = "normal" if priority is None else priority
    if chosen not in PRIORITIES:
        raise ApiError(400, "invalid_priority", f"the priority must be one of: {', '.join(PRIORITIES)}")
    created = clock.now()
    due = created + timedelta(hours=SLA_HOURS[chosen])
    return tickets_repo.create(
        get_db(),
        title=title,
        description=description.strip(),
        priority=chosen,
        requester_id=user.id,
        assignee_id=pick_assignee(),
        created_at=clock.iso(created),
        due_at=clock.iso(due),
    )


def list_tickets(user: User, *, status: str | None, priority: str | None, assignee_id: int | None,
                 text: str | None, page: int, per_page: int) -> dict[str, Any]:
    if status is not None and status not in STATUSES:
        raise ApiError(400, "invalid_status", f"the status must be one of: {', '.join(STATUSES)}")
    if priority is not None and priority not in PRIORITIES:
        raise ApiError(400, "invalid_priority", f"the priority must be one of: {', '.join(PRIORITIES)}")
    tickets, total = tickets_repo.search(
        get_db(),
        requester_id=user.id if user.role == "customer" else None,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        text=text,
        limit=per_page,
        offset=(page - 1) * per_page,
    )
    return {
        "items": [ticket.to_dict() for ticket in tickets],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(1, -(-total // per_page)),
    }


def change_status(user: User, ticket_id: int, new_status: object) -> Ticket:
    ticket = load_visible(user, ticket_id)
    if not isinstance(new_status, str) or new_status not in STATUSES:
        raise ApiError(400, "invalid_status", f"the status must be one of: {', '.join(STATUSES)}")
    if new_status not in TRANSITIONS[ticket.status]:
        raise ApiError(409, "bad_transition", f"a {ticket.status} ticket cannot become {new_status}")
    if user.role == "customer" and not (ticket.status == "resolved" and new_status in ("closed", "open")):
        raise ApiError(403, "forbidden", "a customer can only close or reopen a resolved ticket")

    stamp = clock.iso(clock.now())
    fields: dict[str, Any] = {"status": new_status, "updated_at": stamp}
    if new_status == "in_progress" and ticket.assignee_id is None:
        if user.role != "agent":
            raise ApiError(409, "needs_assignee", "assign an agent before starting work on this ticket")
        fields["assignee_id"] = user.id  # an agent who starts an unassigned ticket takes it
    if new_status == "resolved":
        fields["resolved_at"] = stamp
    elif new_status == "closed":
        fields["closed_at"] = stamp
    elif new_status == "open":  # a reopened ticket starts again
        fields["resolved_at"] = None
        fields["closed_at"] = None
    return tickets_repo.update(get_db(), ticket.id, fields)


def assign(user: User, ticket_id: int, agent_id: object) -> Ticket:
    ticket = load_visible(user, ticket_id)
    if ticket.status == "closed":
        raise ApiError(409, "ticket_closed", "a closed ticket cannot be assigned")
    if not isinstance(agent_id, int) or isinstance(agent_id, bool):
        raise ApiError(400, "invalid_input", "agent_id must be a number")
    agent = users_repo.get(get_db(), agent_id)
    if agent is None or agent.role != "agent":
        raise ApiError(400, "invalid_agent", "agent_id must be the id of an agent")
    return tickets_repo.update(get_db(), ticket.id, {"assignee_id": agent.id, "updated_at": clock.iso(clock.now())})
