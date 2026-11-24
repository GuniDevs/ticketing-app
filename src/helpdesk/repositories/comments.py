from __future__ import annotations

import sqlite3

from ..models import Comment


def add(db: sqlite3.Connection, *, ticket_id: int, author_id: int, body: str, internal: bool, created_at: str) -> Comment:
    cursor = db.execute(
        "INSERT INTO comments (ticket_id, author_id, body, internal, created_at) VALUES (?, ?, ?, ?, ?)",
        (ticket_id, author_id, body, 1 if internal else 0, created_at),
    )
    db.commit()
    row = db.execute("SELECT * FROM comments WHERE id = ?", (cursor.lastrowid,)).fetchone()
    if row is None:
        raise LookupError("the new comment could not be read back")
    return Comment.from_row(row)


def for_ticket(db: sqlite3.Connection, ticket_id: int, include_internal: bool) -> list[Comment]:
    if include_internal:
        rows = db.execute("SELECT * FROM comments WHERE ticket_id = ? ORDER BY id", (ticket_id,)).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM comments WHERE ticket_id = ? AND internal = 0 ORDER BY id", (ticket_id,)
        ).fetchall()
    return [Comment.from_row(row) for row in rows]
