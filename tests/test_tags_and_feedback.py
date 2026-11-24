from conftest import new_ticket
from test_workflow import set_status


def add_tag(client, headers, tid, tag):
    return client.post(f"/api/tickets/{tid}/tags", json={"tag": tag}, headers=headers)


def test_tags_are_cleaned_and_limited(client, customer):
    tid = new_ticket(client, customer[1])["id"]
    first = add_tag(client, customer[1], tid, "  Billing ")
    assert first.status_code == 201
    assert first.get_json()["items"] == ["billing"]
    assert add_tag(client, customer[1], tid, "billing").get_json()["items"] == ["billing"]  # no duplicate

    for bad in ("", "has space", "-start", "x" * 25, None, 5):
        assert add_tag(client, customer[1], tid, bad).status_code == 400

    for number in range(7):
        assert add_tag(client, customer[1], tid, f"t{number}").status_code == 201
    too_many = add_tag(client, customer[1], tid, "one-more")
    assert too_many.status_code == 409
    assert too_many.get_json()["error"]["code"] == "too_many_tags"


def test_tag_visibility_and_removal(client, make_user, customer, agent):
    _, other = make_user("customer", "eve@example.com", "Eve")
    tid = new_ticket(client, customer[1])["id"]
    assert add_tag(client, other, tid, "peek").status_code == 404  # not their ticket
    add_tag(client, agent[1], tid, "vip")

    assert client.delete(f"/api/tickets/{tid}/tags/vip", headers=customer[1]).status_code == 403
    assert client.delete(f"/api/tickets/{tid}/tags/nope", headers=agent[1]).status_code == 404
    removed = client.delete(f"/api/tickets/{tid}/tags/vip", headers=agent[1])
    assert removed.status_code == 200 and removed.get_json()["items"] == []


def test_tag_usage_and_search(client, customer, agent):
    first = new_ticket(client, customer[1], title="Invoice wrong")["id"]
    second = new_ticket(client, customer[1], title="Invoice missing")["id"]
    third = new_ticket(client, customer[1], title="Cannot log in")["id"]
    add_tag(client, agent[1], first, "billing")
    add_tag(client, agent[1], second, "billing")
    add_tag(client, agent[1], third, "login")

    usage = client.get("/api/tags", headers=agent[1]).get_json()["items"]
    assert usage == [{"tag": "billing", "tickets": 2}, {"tag": "login", "tickets": 1}]
    found = client.get("/api/tags/billing/tickets", headers=agent[1]).get_json()["items"]
    assert [t["id"] for t in found] == [second, first]
    assert client.get("/api/tags", headers=customer[1]).status_code == 403
    assert client.get("/api/tags/Bad Tag/tickets", headers=agent[1]).status_code == 400


def test_history_records_what_happened(client, customer, agent, clock):
    tid = new_ticket(client, customer[1])["id"]
    set_status(client, agent[1], tid, "in_progress")
    add_tag(client, agent[1], tid, "hardware")
    client.post(f"/api/tickets/{tid}/assign", json={"agent_id": agent[0].id}, headers=agent[1])

    events = client.get(f"/api/tickets/{tid}/history", headers=agent[1]).get_json()["items"]
    assert [(e["action"], e["detail"]) for e in events] == [
        ("created", "normal"),
        ("status_changed", "open -> in_progress"),
        ("tag_added", "hardware"),
        ("assigned", str(agent[0].id)),
    ]
    assert events[1]["actor_id"] == agent[0].id
    assert client.get(f"/api/tickets/{tid}/history", headers=customer[1]).status_code == 403


def test_rating_rules(client, make_user, customer, agent):
    _, other = make_user("customer", "mallory@example.com", "Mallory")
    tid = new_ticket(client, customer[1])["id"]
    url = f"/api/tickets/{tid}/rating"

    early = client.post(url, json={"score": 5}, headers=customer[1])
    assert early.status_code == 409 and early.get_json()["error"]["code"] == "not_resolved"

    set_status(client, agent[1], tid, "in_progress")
    set_status(client, agent[1], tid, "resolved")
    assert client.post(url, json={"score": 5}, headers=other).status_code == 404
    assert client.post(url, json={"score": 5}, headers=agent[1]).status_code == 403
    for bad in (0, 6, "5", True, None, 4.5):
        assert client.post(url, json={"score": bad}, headers=customer[1]).status_code == 400
    assert client.post(url, json={"score": 4, "feedback": 12}, headers=customer[1]).status_code == 400
    assert client.get(url, headers=customer[1]).status_code == 404  # nothing yet

    done = client.post(url, json={"score": 4, "feedback": " Quick fix "}, headers=customer[1])
    assert done.status_code == 201
    assert done.get_json()["feedback"] == "Quick fix"
    again = client.post(url, json={"score": 1}, headers=customer[1])
    assert again.status_code == 409 and again.get_json()["error"]["code"] == "already_rated"
    assert client.get(url, headers=agent[1]).get_json()["score"] == 4


def test_ratings_reach_the_report(client, customer, agent):
    for score in (5, 3):
        tid = new_ticket(client, customer[1])["id"]
        set_status(client, agent[1], tid, "in_progress")
        set_status(client, agent[1], tid, "resolved")
        client.post(f"/api/tickets/{tid}/rating", json={"score": score}, headers=customer[1])
    add_tag(client, agent[1], tid, "printer")

    data = client.get("/api/reports/summary", headers=agent[1]).get_json()
    assert data["average_rating"] == 4.0
    assert data["rating_count"] == 2
    assert data["agents"][0]["average_rating"] == 4.0
    assert data["top_tags"] == [{"tag": "printer", "tickets": 1}]
