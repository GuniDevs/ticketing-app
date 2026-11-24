"""Passwords, signed tokens and the decorators that protect a route."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from functools import wraps
from typing import Any, Callable

from flask import current_app, g, request

from . import clock
from .db import get_db
from .errors import ApiError
from .repositories import users as users_repo

_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    return hmac.compare_digest(actual, expected)


# Checked when an email is unknown, so a wrong email and a wrong password take about the same time.
DUMMY_HASH = hash_password(secrets.token_hex(8))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> str:
    key = current_app.config["SECRET_KEY"].encode("utf-8")
    return _b64(hmac.new(key, body.encode("ascii"), hashlib.sha256).digest())


def issue_token(user_id: int, role: str) -> str:
    expires = int(clock.now().timestamp()) + int(current_app.config["TOKEN_TTL_S"])
    body = _b64(json.dumps({"uid": user_id, "role": role, "exp": expires}).encode("utf-8"))
    return f"{body}.{_sign(body)}"


def read_token(token: str) -> dict[str, Any]:
    """Returns the token's contents, or raises a 401."""
    try:
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _sign(body)):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(body))
        expires = int(payload["exp"])
        int(payload["uid"])
    except (ValueError, KeyError, TypeError):
        raise ApiError(401, "invalid_token", "the token is not valid") from None
    if expires < int(clock.now().timestamp()):
        raise ApiError(401, "token_expired", "the token has expired, sign in again")
    return payload


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise ApiError(401, "unauthorized", "send the header Authorization: Bearer <token>")
        payload = read_token(token.strip())
        user = users_repo.get(get_db(), int(payload["uid"]))
        if user is None:
            raise ApiError(401, "invalid_token", "the user of this token no longer exists")
        g.user = user  # the role is read from the database, not from the token
        return view(*args, **kwargs)

    return wrapper


def roles_required(*roles: str) -> Callable:
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        @login_required
        def wrapper(*args: Any, **kwargs: Any):
            if g.user.role not in roles:
                raise ApiError(403, "forbidden", "your role is not allowed to do this")
            return view(*args, **kwargs)

        return wrapper

    return decorator
