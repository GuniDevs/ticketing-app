from __future__ import annotations

from typing import Any

from .. import clock
from ..db import get_db
from ..models import ACTIVE_STATUSES, PRIORITIES, STATUSES
from ..repositories import tickets as tickets_repo
from ..repositories import users as users_repo


def summary() -> dict[str, Any]:
    """Numbers for the staff dashboard: counts, SLA, average time to resolve and each agent's workload."""
    db = get_db()
    tickets = tickets_repo.all_tickets(db)
    now = clock.now()

    by_status = {status: 0 for status in STATUSES}
    by_priority = {priority: 0 for priority in PRIORITIES}
    breached = 0
    resolved_hours: list[float] = []
    resolved_on_time = 0

    for ticket in tickets:
        by_status[ticket.status] += 1
        by_priority[ticket.priority] += 1
        due = clock.parse(ticket.due_at)
        if ticket.status in ACTIVE_STATUSES and due < now:
            breached += 1
        if ticket.resolved_at is not None:
            resolved = clock.parse(ticket.resolved_at)
            resolved_hours.append((resolved - clock.parse(ticket.created_at)).total_seconds() / 3600)
            if resolved <= due:
                resolved_on_time += 1

    workload = tickets_repo.active_counts_by_assignee(db)
    agents = [
        {"id": agent.id, "name": agent.name, "active_tickets": workload.get(agent.id, 0)}
        for agent in users_repo.list_all(db, "agent")
    ]
    unassigned = sum(1 for t in tickets if t.assignee_id is None and t.status in ACTIVE_STATUSES)

    return {
        "total": len(tickets),
        "by_status": by_status,
        "by_priority": by_priority,
        "sla_breached": breached,
        "unassigned_active": unassigned,
        "average_resolution_hours": round(sum(resolved_hours) / len(resolved_hours), 2) if resolved_hours else None,
        "sla_met_percent": round(100 * resolved_on_time / len(resolved_hours), 1) if resolved_hours else None,
        "agents": agents,
    }
