from conftest import new_ticket


def set_status(client, headers, ticket_id, status):
    return client.patch(f"/api/tickets/{ticket_id}/status", json={"status": status}, headers=headers)


def test_normal_life_of_a_ticket(client, customer, agent, clock):
    ticket = new_ticket(client, customer[1])
    tid = ticket["id"]
    assert ticket["assignee_id"] == agent[0].id

    assert set_status(client, agent[1], tid, "in_progress").get_json()["status"] == "in_progress"
    clock.advance(hours=3)
    resolved = set_status(client, agent[1], tid, "resolved").get_json()
    assert resolved["resolved_at"] == "2026-01-05T12:00:00+00:00"
    closed = set_status(client, customer[1], tid, "closed").get_json()  # the customer confirms the fix
    assert closed["status"] == "closed"
    assert closed["closed_at"] is not None


def test_moves_that_are_not_allowed(client, customer, agent):
    tid = new_ticket(client, customer[1])["id"]
    jump = set_status(client, agent[1], tid, "resolved")  # open cannot go straight to resolved
    assert jump.status_code == 409
    assert jump.get_json()["error"]["code"] == "bad_transition"
    assert set_status(client, agent[1], tid, "nonsense").status_code == 400
    assert set_status(client, agent[1], tid, None).status_code == 400

    set_status(client, agent[1], tid, "closed")
    assert set_status(client, agent[1], tid, "open").status_code == 409  # closed stays closed


def test_customers_may_only_close_or_reopen_a_resolved_ticket(client, customer, agent):
    tid = new_ticket(client, customer[1])["id"]
    assert set_status(client, customer[1], tid, "in_progress").status_code == 403
    assert set_status(client, customer[1], tid, "closed").status_code == 403  # not resolved yet

    set_status(client, agent[1], tid, "in_progress")
    set_status(client, agent[1], tid, "resolved")
    reopened = set_status(client, customer[1], tid, "open").get_json()
    assert reopened["status"] == "open"
    assert reopened["resolved_at"] is None  # a reopened ticket starts again


def test_an_agent_who_starts_an_unassigned_ticket_takes_it(client, make_user, customer):
    tid = new_ticket(client, customer[1])["id"]  # no agents yet, so unassigned
    later_agent, headers = make_user("agent", "late@example.com", "Late Agent")
    started = set_status(client, headers, tid, "in_progress").get_json()
    assert started["assignee_id"] == later_agent.id


def test_an_admin_cannot_start_an_unassigned_ticket(client, customer, admin):
    tid = new_ticket(client, customer[1])["id"]
    refused = set_status(client, admin[1], tid, "in_progress")
    assert refused.status_code == 409
    assert refused.get_json()["error"]["code"] == "needs_assignee"


def test_a_closed_ticket_cannot_be_assigned(client, customer, agent):
    tid = new_ticket(client, customer[1])["id"]
    set_status(client, agent[1], tid, "closed")
    refused = client.post(f"/api/tickets/{tid}/assign", json={"agent_id": agent[0].id}, headers=agent[1])
    assert refused.status_code == 409


def test_comments_and_internal_notes(client, customer, agent):
    tid = new_ticket(client, customer[1])["id"]
    url = f"/api/tickets/{tid}/comments"

    assert client.post(url, json={"body": "Any news?"}, headers=customer[1]).status_code == 201
    assert client.post(url, json={"body": "Checking the logs."}, headers=agent[1]).status_code == 201
    note = client.post(url, json={"body": "Customer is on the old firmware.", "internal": True}, headers=agent[1])
    assert note.status_code == 201 and note.get_json()["internal"] is True

    assert client.post(url, json={"body": "Sneaky", "internal": True}, headers=customer[1]).status_code == 403
    assert client.post(url, json={"body": "   "}, headers=customer[1]).status_code == 400
    assert client.post(url, json={"body": "x", "internal": "yes"}, headers=customer[1]).status_code == 400

    seen_by_customer = client.get(url, headers=customer[1]).get_json()["items"]
    seen_by_agent = client.get(url, headers=agent[1]).get_json()["items"]
    assert [c["body"] for c in seen_by_customer] == ["Any news?", "Checking the logs."]
    assert len(seen_by_agent) == 3


def test_comments_respect_ownership_and_closed_tickets(client, make_user, customer, agent):
    _, other_headers = make_user("customer", "dave@example.com", "Dave")
    tid = new_ticket(client, customer[1])["id"]
    url = f"/api/tickets/{tid}/comments"
    assert client.get(url, headers=other_headers).status_code == 404
    assert client.post(url, json={"body": "hi"}, headers=other_headers).status_code == 404

    set_status(client, agent[1], tid, "closed")
    closed = client.post(url, json={"body": "one more thing"}, headers=customer[1])
    assert closed.status_code == 409
