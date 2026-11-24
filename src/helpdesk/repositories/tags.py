from __future__ import annotations

import sqlite3

from ..models import Ticket


def add(db: sqlite3.Connection, ticket_id: int, tag: str) -> bool:
    """Adds the tag. False if the ticket already had it."""
    cursor = db.execute("INSERT OR IGNORE INTO ticket_tags (ticket_id, tag) VALUES (?, ?)", (ticket_id, tag))
    db.commit()
    return cursor.rowcount == 1


def remove(db: sqlite3.Connection, ticket_id: int, tag: str) -> bool:
    cursor = db.execute("DELETE FROM ticket_tags WHERE ticket_id = ? AND tag = ?", (ticket_id, tag))
    db.commit()
    return cursor.rowcount == 1


def for_ticket(db: sqlite3.Connection, ticket_id: int) -> list[str]:
    rows = db.execute("SELECT tag FROM ticket_tags WHERE ticket_id = ? ORDER BY tag", (ticket_id,)).fetchall()
    return [row["tag"] for row in rows]


def count_for_ticket(db: sqlite3.Connection, ticket_id: int) -> int:
    return db.execute("SELECT COUNT(*) FROM ticket_tags WHERE ticket_id = ?", (ticket_id,)).fetchone()[0]


def usage(db: sqlite3.Connection) -> list[tuple[str, int]]:
    """Every tag with the number of tickets that carry it, the most used first."""
    rows = db.execute("SELECT tag, COUNT(*) AS n FROM ticket_tags GROUP BY tag ORDER BY n DESC, tag").fetchall()
    return [(row["tag"], row["n"]) for row in rows]


def tickets_with(db: sqlite3.Connection, tag: str) -> list[Ticket]:
    rows = db.execute(
        "SELECT t.* FROM tickets t JOIN ticket_tags g ON g.ticket_id = t.id WHERE g.tag = ? ORDER BY t.id DESC",
        (tag,),
    ).fetchall()
    return [Ticket.from_row(row) for row in rows]
