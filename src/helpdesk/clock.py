"""The current time, in one place, so tests can move it."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app


def now() -> datetime:
    """Current UTC time, or the app's CLOCK function if one is set (tests do that)."""
    clock = current_app.config.get("CLOCK")
    return clock() if clock else datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def parse(text: str) -> datetime:
    return datetime.fromisoformat(text)
