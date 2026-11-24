from __future__ import annotations

from .. import clock
from ..db import get_db
from ..errors import ApiError
from ..models import Comment, User
from ..repositories import comments as comments_repo
from . import ticket_service

BODY_MAX = 5000


def add_comment(user: User, ticket_id: int, body: object, internal: object) -> Comment:
    ticket = ticket_service.load_visible(user, ticket_id)
    if not isinstance(body, str) or not body.strip() or len(body) > BODY_MAX:
        raise ApiError(400, "invalid_body", f"the comment is required, up to {BODY_MAX} characters")
    if not isinstance(internal, bool):
        raise ApiError(400, "invalid_input", "internal must be true or false")
    if internal and user.role == "customer":
        raise ApiError(403, "forbidden", "only staff can write internal notes")
    if ticket.status == "closed":
        raise ApiError(409, "ticket_closed", "a closed ticket takes no new comments; reopen it first")
    return comments_repo.add(
        get_db(),
        ticket_id=ticket.id,
        author_id=user.id,
        body=body.strip(),
        internal=internal,
        created_at=clock.iso(clock.now()),
    )


def list_comments(user: User, ticket_id: int) -> list[Comment]:
    ticket = ticket_service.load_visible(user, ticket_id)
    return comments_repo.for_ticket(get_db(), ticket.id, include_internal=user.role != "customer")
