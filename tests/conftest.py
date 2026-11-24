from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from helpdesk import create_app
from helpdesk.services import user_service

PASSWORD = "correct-horse-battery"


class FakeClock:
    """A clock tests can move forward."""

    def __init__(self) -> None:
        self.moment = datetime(2026, 1, 5, 9, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, **kwargs: float) -> None:
        self.moment += timedelta(**kwargs)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def app(tmp_path, clock):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
        "SECRET_KEY": "test-secret",
        "TOKEN_TTL_S": 3 * 24 * 3600,  # long enough that tests moving the clock by hours stay signed in
        "CLOCK": clock,
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    """make_user("agent", "ann@example.com") creates the user and returns (user, auth headers)."""

    def _make(role: str, email: str, name: str = "Test User"):
        with app.app_context():
            user = user_service.create_user(email, name, PASSWORD, role)
        response = app.test_client().post("/api/auth/login", json={"email": email, "password": PASSWORD})
        token = response.get_json()["token"]
        return user, {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def customer(make_user):
    return make_user("customer", "carol@example.com", "Carol")


@pytest.fixture
def agent(make_user):
    return make_user("agent", "ann@example.com", "Ann")


@pytest.fixture
def admin(make_user):
    return make_user("admin", "root@example.com", "Root")


def new_ticket(client, headers, title="Printer is broken", priority="normal"):
    response = client.post(
        "/api/tickets",
        json={"title": title, "description": "It prints blank pages.", "priority": priority},
        headers=headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()
