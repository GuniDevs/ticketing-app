from __future__ import annotations

import sqlite3

from ..models import Rating


def get(db: sqlite3.Connection, ticket_id: int) -> Rating | None:
    row = db.execute("SELECT * FROM ratings WHERE ticket_id = ?", (ticket_id,)).fetchone()
    return Rating.from_row(row) if row else None


def create(db: sqlite3.Connection, *, ticket_id: int, score: int, feedback: str, created_at: str) -> Rating:
    db.execute(
        "INSERT INTO ratings (ticket_id, score, feedback, created_at) VALUES (?, ?, ?, ?)",
        (ticket_id, score, feedback, created_at),
    )
    db.commit()
    created = get(db, ticket_id)
    if created is None:
        raise LookupError("the new rating could not be read back")
    return created


def average_and_count(db: sqlite3.Connection) -> tuple[float | None, int]:
    row = db.execute("SELECT AVG(score) AS mean, COUNT(*) AS n FROM ratings").fetchone()
    return (round(row["mean"], 2) if row["mean"] is not None else None), row["n"]


def average_by_assignee(db: sqlite3.Connection) -> dict[int, float]:
    rows = db.execute(
        "SELECT t.assignee_id AS agent, AVG(r.score) AS mean FROM ratings r "
        "JOIN tickets t ON t.id = r.ticket_id WHERE t.assignee_id IS NOT NULL GROUP BY t.assignee_id"
    ).fetchall()
    return {row["agent"]: round(row["mean"], 2) for row in rows}
