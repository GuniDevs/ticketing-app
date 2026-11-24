from __future__ import annotations

import sqlite3

from ..models import TicketEvent


def add(db: sqlite3.Connection, *, ticket_id: int, actor_id: int, action: str, detail: str, created_at: str) -> None:
    db.execute(
        "INSERT INTO ticket_events (ticket_id, actor_id, action, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (ticket_id, actor_id, action, detail, created_at),
    )
    db.commit()


def for_ticket(db: sqlite3.Connection, ticket_id: int) -> list[TicketEvent]:
    rows = db.execute("SELECT * FROM ticket_events WHERE ticket_id = ? ORDER BY id", (ticket_id,)).fetchall()
    return [TicketEvent.from_row(row) for row in rows]
