from __future__ import annotations

import re

from .. import clock
from ..db import get_db
from ..errors import ApiError
from ..models import Ticket, User
from ..repositories import tags as tags_repo
from ..repositories import tickets as tickets_repo
from . import history_service, ticket_service

TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,23}$")
MAX_TAGS_PER_TICKET = 8


def clean(tag: object) -> str:
    name = tag.strip().lower() if isinstance(tag, str) else ""
    if not TAG_PATTERN.match(name):
        raise ApiError(400, "invalid_tag", "a tag is 1 to 24 letters, digits or dashes, and starts with a letter or digit")
    return name


def add_tag(user: User, ticket_id: int, tag: object) -> list[str]:
    ticket = ticket_service.load_visible(user, ticket_id)
    name = clean(tag)
    db = get_db()
    if tags_repo.count_for_ticket(db, ticket.id) >= MAX_TAGS_PER_TICKET:
        raise ApiError(409, "too_many_tags", f"a ticket can have at most {MAX_TAGS_PER_TICKET} tags")
    if tags_repo.add(db, ticket.id, name):
        tickets_repo.update(db, ticket.id, {"updated_at": clock.iso(clock.now())})
        history_service.record(user, ticket.id, "tag_added", name)
    return tags_repo.for_ticket(db, ticket.id)


def remove_tag(user: User, ticket_id: int, tag: str) -> list[str]:
    ticket = ticket_service.load_visible(user, ticket_id)
    name = clean(tag)
    db = get_db()
    if not tags_repo.remove(db, ticket.id, name):
        raise ApiError(404, "not_found", "the ticket does not have that tag")
    history_service.record(user, ticket.id, "tag_removed", name)
    return tags_repo.for_ticket(db, ticket.id)


def list_for_ticket(user: User, ticket_id: int) -> list[str]:
    ticket = ticket_service.load_visible(user, ticket_id)
    return tags_repo.for_ticket(get_db(), ticket.id)


def usage() -> list[dict[str, object]]:
    return [{"tag": tag, "tickets": count} for tag, count in tags_repo.usage(get_db())]


def tickets_with(tag: str) -> list[Ticket]:
    return tags_repo.tickets_with(get_db(), clean(tag))
