from conftest import new_ticket


def test_ticket_gets_an_sla_due_date_by_priority(client, customer):
    urgent = new_ticket(client, customer[1], priority="urgent")
    low = new_ticket(client, customer[1], title="Slow wifi", priority="low")
    assert urgent["created_at"] == "2026-01-05T09:00:00+00:00"
    assert urgent["due_at"] == "2026-01-05T13:00:00+00:00"  # urgent: 4 hours
    assert low["due_at"] == "2026-01-08T09:00:00+00:00"  # low: 72 hours
    assert urgent["status"] == "open"


def test_ticket_validation(client, customer):
    headers = customer[1]
    assert client.post("/api/tickets", json={"title": "ab", "description": "x"}, headers=headers).status_code == 400
    assert client.post("/api/tickets", json={"title": "Fine title", "description": ""}, headers=headers).status_code == 400
    bad_priority = client.post(
        "/api/tickets", json={"title": "Fine title", "description": "x", "priority": "panic"}, headers=headers
    )
    assert bad_priority.get_json()["error"]["code"] == "invalid_priority"
    default = client.post("/api/tickets", json={"title": "Fine title", "description": "x"}, headers=headers)
    assert default.get_json()["priority"] == "normal"


def test_tickets_go_to_the_least_loaded_agent(client, make_user, customer):
    first, _ = make_user("agent", "a1@example.com", "Agent One")
    second, _ = make_user("agent", "a2@example.com", "Agent Two")
    owners = [new_ticket(client, customer[1], title=f"Problem {n}")["assignee_id"] for n in range(4)]
    assert owners == [first.id, second.id, first.id, second.id]


def test_no_agents_means_unassigned(client, customer):
    assert new_ticket(client, customer[1])["assignee_id"] is None


def test_customers_only_see_their_own_tickets(client, make_user, customer, agent):
    other, other_headers = make_user("customer", "dave@example.com", "Dave")
    mine = new_ticket(client, customer[1], title="Mine")
    theirs = new_ticket(client, other_headers, title="Theirs")

    seen = client.get("/api/tickets", headers=customer[1]).get_json()
    assert [t["title"] for t in seen["items"]] == ["Mine"]
    assert client.get(f"/api/tickets/{mine['id']}", headers=customer[1]).status_code == 200
    # someone else's ticket looks exactly like a missing one
    assert client.get(f"/api/tickets/{theirs['id']}", headers=customer[1]).status_code == 404
    assert client.get("/api/tickets/9999", headers=customer[1]).status_code == 404

    staff_view = client.get("/api/tickets", headers=agent[1]).get_json()
    assert staff_view["total"] == 2


def test_filters_search_and_paging(client, agent, customer):
    for n in range(5):
        new_ticket(client, customer[1], title=f"Printer jam {n}", priority="high")
    new_ticket(client, customer[1], title="100% broken_screen", priority="low")
    headers = agent[1]

    page_one = client.get("/api/tickets?per_page=4", headers=headers).get_json()
    assert page_one["total"] == 6 and page_one["pages"] == 2 and len(page_one["items"]) == 4
    assert page_one["items"][0]["id"] > page_one["items"][-1]["id"]  # newest first
    page_two = client.get("/api/tickets?per_page=4&page=2", headers=headers).get_json()
    assert len(page_two["items"]) == 2

    assert client.get("/api/tickets?priority=high", headers=headers).get_json()["total"] == 5
    assert client.get("/api/tickets?q=jam", headers=headers).get_json()["total"] == 5
    # % and _ in a search are plain characters, not wildcards
    assert client.get("/api/tickets?q=100%25", headers=headers).get_json()["total"] == 1
    assert client.get("/api/tickets?q=%25", headers=headers).get_json()["total"] == 1
    assert client.get("/api/tickets?q=broken_screen", headers=headers).get_json()["total"] == 1
    assert client.get("/api/tickets?q=brokenXscreen", headers=headers).get_json()["total"] == 0


def test_bad_query_values_are_refused(client, agent):
    headers = agent[1]
    for query in ("status=done", "priority=panic", "page=0", "per_page=1000", "per_page=abc", "assignee_id=x"):
        assert client.get(f"/api/tickets?{query}", headers=headers).status_code == 400, query


def test_assigning_a_ticket(client, make_user, customer, agent):
    other_agent, _ = make_user("agent", "bo@example.com", "Bo")
    ticket = new_ticket(client, customer[1])

    assert client.post(f"/api/tickets/{ticket['id']}/assign", json={"agent_id": other_agent.id}, headers=customer[1]).status_code == 403
    moved = client.post(f"/api/tickets/{ticket['id']}/assign", json={"agent_id": other_agent.id}, headers=agent[1])
    assert moved.status_code == 200
    assert moved.get_json()["assignee_id"] == other_agent.id

    not_an_agent = client.post(f"/api/tickets/{ticket['id']}/assign", json={"agent_id": customer[0].id}, headers=agent[1])
    assert not_an_agent.get_json()["error"]["code"] == "invalid_agent"
    wrong_type = client.post(f"/api/tickets/{ticket['id']}/assign", json={"agent_id": "1"}, headers=agent[1])
    assert wrong_type.status_code == 400
