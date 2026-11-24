from __future__ import annotations

import sqlite3

from ..models import User


def create(db: sqlite3.Connection, email: str, name: str, role: str, password_hash: str, created_at: str) -> User:
    """Raises sqlite3.IntegrityError when the email is already taken."""
    cursor = db.execute(
        "INSERT INTO users (email, name, role, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        (email, name, role, password_hash, created_at),
    )
    db.commit()
    user = get(db, cursor.lastrowid) if cursor.lastrowid is not None else None
    if user is None:
        raise LookupError("the new user could not be read back")
    return user


def get(db: sqlite3.Connection, user_id: int) -> User | None:
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return User.from_row(row) if row else None


def get_by_email(db: sqlite3.Connection, email: str) -> User | None:
    row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return User.from_row(row) if row else None


def list_all(db: sqlite3.Connection, role: str | None = None) -> list[User]:
    if role is None:
        rows = db.execute("SELECT * FROM users ORDER BY id").fetchall()
    else:
        rows = db.execute("SELECT * FROM users WHERE role = ? ORDER BY id", (role,)).fetchall()
    return [User.from_row(row) for row in rows]
