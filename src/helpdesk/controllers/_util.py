from __future__ import annotations

from typing import Any

from flask import current_app, request

from ..errors import ApiError


def json_body() -> dict[str, Any]:
    """The request's JSON object, or a 400."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, "invalid_json", "send a JSON object as the request body")
    return body


def int_arg(name: str, default: int, *, minimum: int, maximum: int | None = None) -> int:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ApiError(400, "invalid_query", f"{name} must be a whole number") from None
    if value < minimum or (maximum is not None and value > maximum):
        limit = f"{minimum} to {maximum}" if maximum is not None else f"at least {minimum}"
        raise ApiError(400, "invalid_query", f"{name} must be {limit}")
    return value


def optional_int_arg(name: str) -> int | None:
    if request.args.get(name) in (None, ""):
        return None
    return int_arg(name, 0, minimum=1)


def max_per_page() -> int:
    return int(current_app.config["MAX_PER_PAGE"])
