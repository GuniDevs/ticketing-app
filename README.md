# helpdesk-api

A small helpdesk ticketing API in Python (Flask and SQLite). Customers open tickets, agents work them, admins manage staff
and read reports.

## What it does

- **Roles:** `customer`, `agent`, `admin`. Anyone can sign up, and a sign-up is always a customer. Only an admin creates agents.
- **Tickets:** a priority sets the SLA due date (urgent 4 h, high 8 h, normal 24 h, low 72 h). A new ticket goes to the agent with the
  fewest open tickets.
- **Workflow:** `open` → `in_progress` → `resolved` → `closed`, plus reopening. A customer may only close or reopen a resolved ticket
  of their own. A closed ticket stays closed.
- **Comments:** staff can write internal notes that a customer never sees. A closed ticket takes no new comments.
- **Reports (staff):** counts by status and priority, SLA breaches, average time to resolve, SLA met percent, and each agent's workload.
- **Safety:** passwords are hashed with scrypt, tokens are signed (HMAC-SHA256) and expire, every SQL value goes through a placeholder,
  and a customer who asks for someone else's ticket gets the same 404 as for a missing one.

## Layout

| Folder | Job |
| --- | --- |
| `src/helpdesk/controllers/` | Five controllers: auth, users, tickets, comments, reports. They read the request and shape the JSON answer |
| `src/helpdesk/services/` | The business rules |
| `src/helpdesk/repositories/` | The only code that talks SQL |
| `src/helpdesk/auth.py` | Passwords, tokens and the `login_required` and `roles_required` decorators |
| `src/helpdesk/models.py` | Data classes and the fixed rules (roles, priorities, SLA hours, allowed status moves) |
| `tests/` | pytest tests |

## Run and test

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
.venv/bin/python -m pytest
HELPDESK_SECRET=change-me .venv/bin/python -m helpdesk      # serves on http://127.0.0.1:5000
```

Settings come from the environment: `HELPDESK_DB` (database file, default `helpdesk.db`) and `HELPDESK_SECRET` (token key; without it
a new key is made at each start, so tokens stop working after a restart).

## API

| Method and path | Who | What |
| --- | --- | --- |
| `POST /api/auth/register` | anyone | `{email, name, password}` |
| `POST /api/auth/login` | anyone | `{email, password}` → `{token, user}` |
| `GET /api/auth/me` | signed in | the current user |
| `POST /api/users` | admin | create a user with a role |
| `GET /api/users`, `GET /api/users/<id>` | staff | list (`?role=`) or read |
| `POST /api/tickets` | signed in | `{title, description, priority}` |
| `GET /api/tickets` | signed in | `?status=&priority=&assignee_id=&q=&page=&per_page=` |
| `GET /api/tickets/<id>` | signed in | one ticket |
| `PATCH /api/tickets/<id>/status` | signed in | `{status}` |
| `POST /api/tickets/<id>/assign` | staff | `{agent_id}` |
| `GET`, `POST /api/tickets/<id>/comments` | signed in | `{body, internal}` |
| `GET /api/reports/summary` | staff | the numbers above |
| `GET /healthz` | anyone | `{"status": "ok"}` |

Send the token as `Authorization: Bearer <token>`.
