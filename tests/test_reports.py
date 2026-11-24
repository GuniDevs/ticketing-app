from conftest import new_ticket
from test_workflow import set_status


def test_reports_are_for_staff_only(client, customer, agent):
    assert client.get("/api/reports/summary", headers=customer[1]).status_code == 403
    assert client.get("/api/reports/summary").status_code == 401
    assert client.get("/api/reports/summary", headers=agent[1]).status_code == 200


def test_empty_summary(client, agent):
    data = client.get("/api/reports/summary", headers=agent[1]).get_json()
    assert data["total"] == 0
    assert data["average_resolution_hours"] is None
    assert data["sla_met_percent"] is None
    assert data["agents"] == [{"id": agent[0].id, "name": "Ann", "active_tickets": 0}]


def test_summary_counts_sla_and_workload(client, customer, agent, clock):
    urgent = new_ticket(client, customer[1], title="Server down", priority="urgent")  # due in 4 hours
    quick = new_ticket(client, customer[1], title="Reset password", priority="normal")  # due in 24 hours
    new_ticket(client, customer[1], title="Slow laptop", priority="low")

    set_status(client, agent[1], quick["id"], "in_progress")
    clock.advance(hours=2)
    set_status(client, agent[1], quick["id"], "resolved")  # resolved after 2 hours: on time
    clock.advance(hours=3)  # now 5 hours after creation: the urgent ticket is past its 4 hour SLA

    data = client.get("/api/reports/summary", headers=agent[1]).get_json()
    assert data["total"] == 3
    assert data["by_status"] == {"open": 2, "in_progress": 0, "resolved": 1, "closed": 0}
    assert data["by_priority"]["urgent"] == 1
    assert data["sla_breached"] == 1  # only the urgent ticket, still open
    assert data["average_resolution_hours"] == 2.0
    assert data["sla_met_percent"] == 100.0
    assert data["agents"][0]["active_tickets"] == 2
    assert data["unassigned_active"] == 0
    assert urgent["id"] != quick["id"]


def test_late_resolution_counts_against_the_sla(client, customer, agent, clock):
    ticket = new_ticket(client, customer[1], priority="urgent")
    set_status(client, agent[1], ticket["id"], "in_progress")
    clock.advance(hours=6)
    set_status(client, agent[1], ticket["id"], "resolved")
    data = client.get("/api/reports/summary", headers=agent[1]).get_json()
    assert data["sla_met_percent"] == 0.0
    assert data["average_resolution_hours"] == 6.0
    assert data["sla_breached"] == 0  # it is resolved now, so it no longer counts as breached


def test_health_and_unknown_routes(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}
    missing = client.get("/api/nothing-here")
    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "not_found"
    assert client.delete("/api/tickets").status_code == 405
