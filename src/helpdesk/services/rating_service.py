from __future__ import annotations

from .. import clock
from ..db import get_db
from ..errors import ApiError
from ..models import Rating, User
from ..repositories import ratings as ratings_repo
from . import history_service, ticket_service

FEEDBACK_MAX = 1000


def rate(user: User, ticket_id: int, score: object, feedback: object) -> Rating:
    """Only the customer who opened the ticket can rate it, once, after it is resolved or closed."""
    ticket = ticket_service.load_visible(user, ticket_id)
    if ticket.requester_id != user.id:
        raise ApiError(403, "forbidden", "only the person who opened the ticket can rate it")
    if ticket.status not in ("resolved", "closed"):
        raise ApiError(409, "not_resolved", "a ticket can be rated once it is resolved")
    if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
        raise ApiError(400, "invalid_score", "the score must be a whole number from 1 to 5")
    text = "" if feedback is None else feedback
    if not isinstance(text, str) or len(text) > FEEDBACK_MAX:
        raise ApiError(400, "invalid_feedback", f"the feedback must be text of up to {FEEDBACK_MAX} characters")
    db = get_db()
    if ratings_repo.get(db, ticket.id) is not None:
        raise ApiError(409, "already_rated", "this ticket has already been rated")
    rating = ratings_repo.create(
        db, ticket_id=ticket.id, score=score, feedback=text.strip(), created_at=clock.iso(clock.now())
    )
    history_service.record(user, ticket.id, "rated", str(score))
    return rating


def get_rating(user: User, ticket_id: int) -> Rating:
    ticket = ticket_service.load_visible(user, ticket_id)
    rating = ratings_repo.get(get_db(), ticket.id)
    if rating is None:
        raise ApiError(404, "not_found", "this ticket has no rating yet")
    return rating
