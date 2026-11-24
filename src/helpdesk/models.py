"""Plain data classes and the fixed rules of the helpdesk (roles, priorities, statuses, SLA, allowed moves)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

ROLES = ("customer", "agent", "admin")
PRIORITIES = ("low", "normal", "high", "urgent")
STATUSES = ("open", "in_progress", "resolved", "closed")

# Hours from creation until a ticket of this priority should be resolved.
SLA_HOURS = {"urgent": 4, "high": 8, "normal": 24, "low": 72}

# Which status a ticket may move to from each status. A closed ticket stays closed.
TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "closed"},
    "in_progress": {"resolved", "open"},
    "resolved": {"closed", "open"},
    "closed": set(),
}

# Statuses where the ticket still needs work (it counts against an agent's workload and can breach its SLA).
ACTIVE_STATUSES = ("open", "in_progress")


@dataclass
class User:
    id: int
    email: str
    name: str
    role: str
    password_hash: str
    created_at: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "User":
        return cls(**{key: row[key] for key in ("id", "email", "name", "role", "password_hash", "created_at")})

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        del data["password_hash"]
        return data


@dataclass
class Ticket:
    id: int
    title: str
    description: str
    priority: str
    status: str
    requester_id: int
    assignee_id: int | None
    created_at: str
    updated_at: str
    due_at: str
    resolved_at: str | None
    closed_at: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Ticket":
        names = (
            "id", "title", "description", "priority", "status", "requester_id", "assignee_id",
            "created_at", "updated_at", "due_at", "resolved_at", "closed_at",
        )
        return cls(**{key: row[key] for key in names})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Comment:
    id: int
    ticket_id: int
    author_id: int
    body: str
    internal: bool
    created_at: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Comment":
        return cls(
            id=row["id"],
            ticket_id=row["ticket_id"],
            author_id=row["author_id"],
            body=row["body"],
            internal=bool(row["internal"]),
            created_at=row["created_at"],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
