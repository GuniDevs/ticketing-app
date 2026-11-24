from __future__ import annotations

import re
import sqlite3

from .. import clock
from ..auth import DUMMY_HASH, hash_password, verify_password
from ..db import get_db
from ..errors import ApiError
from ..models import ROLES, User
from ..repositories import users as users_repo

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


def _clean(email: object, name: object, password: object) -> tuple[str, str, str]:
    if not isinstance(email, str) or not isinstance(name, str) or not isinstance(password, str):
        raise ApiError(400, "invalid_input", "email, name and password must be text")
    email = email.strip().lower()
    name = name.strip()
    if len(email) > 254 or not _EMAIL.match(email):
        raise ApiError(400, "invalid_email", "that is not a valid email address")
    if not 1 <= len(name) <= 80:
        raise ApiError(400, "invalid_name", "the name must be 1 to 80 characters")
    if len(password) < MIN_PASSWORD:
        raise ApiError(400, "weak_password", f"the password must be at least {MIN_PASSWORD} characters")
    return email, name, password


def create_user(email: object, name: object, password: object, role: str = "customer") -> User:
    if role not in ROLES:
        raise ApiError(400, "invalid_role", f"the role must be one of: {', '.join(ROLES)}")
    email, name, password = _clean(email, name, password)
    try:
        return users_repo.create(get_db(), email, name, role, hash_password(password), clock.iso(clock.now()))
    except sqlite3.IntegrityError:
        raise ApiError(409, "email_taken", "an account with this email already exists") from None


def register(email: object, name: object, password: object) -> User:
    """Public sign-up: always a customer."""
    return create_user(email, name, password, "customer")


def authenticate(email: object, password: object) -> User:
    if not isinstance(email, str) or not isinstance(password, str):
        raise ApiError(400, "invalid_input", "email and password must be text")
    user = users_repo.get_by_email(get_db(), email.strip().lower())
    stored = user.password_hash if user else DUMMY_HASH
    if not verify_password(password, stored) or user is None:
        raise ApiError(401, "bad_credentials", "wrong email or password")
    return user


def list_users(role: str | None) -> list[User]:
    if role is not None and role not in ROLES:
        raise ApiError(400, "invalid_role", f"the role must be one of: {', '.join(ROLES)}")
    return users_repo.list_all(get_db(), role)


def get_user(user_id: int) -> User:
    user = users_repo.get(get_db(), user_id)
    if user is None:
        raise ApiError(404, "not_found", "user not found")
    return user
