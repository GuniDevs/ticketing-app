from __future__ import annotations

import sqlite3
from typing import Any

from ..models import Ticket

# The columns an update may change. Anything else is refused, so a column name never comes from a caller.
UPDATABLE = ("status", "assignee_id", "updated_at", "resolved_at", "closed_at")


def create(db: sqlite3.Connection, *, title: str, description: str, priority: str, requester_id: int,
           assignee_id: int | None, created_at: str, due_at: str) -> Ticket:
    cursor = db.execute(
        "INSERT INTO tickets (title, description, priority, status, requester_id, assignee_id, "
        "created_at, updated_at, due_at) VALUES (?, ?, ?, 'open', ?, ?, ?, ?, ?)",
        (title, description, priority, requester_id, assignee_id, created_at, created_at, due_at),
    )
    db.commit()
    return _must_get(db, cursor.lastrowid)


def _must_get(db: sqlite3.Connection, ticket_id: int | None) -> Ticket:
    ticket = get(db, ticket_id) if ticket_id is not None else None
    if ticket is None:
        raise LookupError(f"ticket {ticket_id} not found")
    return ticket


def get(db: sqlite3.Connection, ticket_id: int) -> Ticket | None:
    row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return Ticket.from_row(row) if row else None


def update(db: sqlite3.Connection, ticket_id: int, fields: dict[str, Any]) -> Ticket:
    unknown = set(fields) - set(UPDATABLE)
    if unknown or not fields:
        raise ValueError(f"cannot update {sorted(unknown) or 'nothing'}")
    names = [name for name in UPDATABLE if name in fields]
    assignments = ", ".join(f"{name} = ?" for name in names)
    db.execute(f"UPDATE tickets SET {assignments} WHERE id = ?", [*(fields[name] for name in names), ticket_id])  # noqa: S608
    db.commit()
    return _must_get(db, ticket_id)


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search(db: sqlite3.Connection, *, requester_id: int | None = None, status: str | None = None,
           priority: str | None = None, assignee_id: int | None = None, text: str | None = None,
           limit: int = 20, offset: int = 0) -> tuple[list[Ticket], int]:
    """Returns one page of tickets (newest first) and how many tickets match in all."""
    clauses: list[str] = []
    params: list[Any] = []
    if requester_id is not None:
        clauses.append("requester_id = ?")
        params.append(requester_id)
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if priority is not None:
        clauses.append("priority = ?")
        params.append(priority)
    if assignee_id is not None:
        clauses.append("assignee_id = ?")
        params.append(assignee_id)
    if text:
        clauses.append("title LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(text)}%")
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    total = db.execute(f"SELECT COUNT(*) FROM tickets{where}", params).fetchone()[0]  # noqa: S608
    rows = db.execute(
        f"SELECT * FROM tickets{where} ORDER BY id DESC LIMIT ? OFFSET ?",  # noqa: S608
        [*params, limit, offset],
    ).fetchall()
    return [Ticket.from_row(row) for row in rows], total


def all_tickets(db: sqlite3.Connection) -> list[Ticket]:
    return [Ticket.from_row(row) for row in db.execute("SELECT * FROM tickets ORDER BY id").fetchall()]


def active_counts_by_assignee(db: sqlite3.Connection) -> dict[int, int]:
    rows = db.execute(
        "SELECT assignee_id, COUNT(*) AS n FROM tickets "
        "WHERE assignee_id IS NOT NULL AND status IN ('open', 'in_progress') GROUP BY assignee_id"
    ).fetchall()
    return {row["assignee_id"]: row["n"] for row in rows}
