from __future__ import annotations

from .. import clock
from ..db import get_db
from ..models import TicketEvent, User
from ..repositories import events as events_repo


def record(user: User, ticket_id: int, action: str, detail: str) -> None:
    """Writes one line to the ticket's history."""
    events_repo.add(
        get_db(),
        ticket_id=ticket_id,
        actor_id=user.id,
        action=action,
        detail=detail,
        created_at=clock.iso(clock.now()),
    )


def history(ticket_id: int) -> list[TicketEvent]:
    """The ticket's history, oldest first. The caller has already checked the ticket is visible."""
    return events_repo.for_ticket(get_db(), ticket_id)
