from conftest import PASSWORD


def test_register_login_and_me(client):
    created = client.post("/api/auth/register", json={"email": "Bob@Example.com", "name": "Bob", "password": PASSWORD})
    assert created.status_code == 201
    assert created.get_json()["email"] == "bob@example.com"  # stored in lower case
    assert created.get_json()["role"] == "customer"
    assert "password_hash" not in created.get_json()

    login = client.post("/api/auth/login", json={"email": "bob@example.com", "password": PASSWORD})
    assert login.status_code == 200
    token = login.get_json()["token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.get_json()["name"] == "Bob"


def test_register_rejects_bad_input(client):
    bad_email = client.post("/api/auth/register", json={"email": "nope", "name": "X", "password": PASSWORD})
    assert bad_email.status_code == 400
    assert bad_email.get_json()["error"]["code"] == "invalid_email"

    short = client.post("/api/auth/register", json={"email": "a@b.co", "name": "X", "password": "short"})
    assert short.get_json()["error"]["code"] == "weak_password"

    not_json = client.post("/api/auth/register", data="plain text")
    assert not_json.status_code == 400


def test_duplicate_email_is_refused(client):
    body = {"email": "dup@example.com", "name": "Dup", "password": PASSWORD}
    assert client.post("/api/auth/register", json=body).status_code == 201
    second = client.post("/api/auth/register", json=body)
    assert second.status_code == 409
    assert second.get_json()["error"]["code"] == "email_taken"


def test_wrong_password_and_unknown_email_look_the_same(client, customer):
    wrong = client.post("/api/auth/login", json={"email": "carol@example.com", "password": "not-the-password"})
    unknown = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()


def test_protected_routes_need_a_valid_token(client, customer):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401

    _, headers = customer
    token = headers["Authorization"].split(" ", 1)[1]
    body, signature = token.split(".")
    tampered = f"{body}.{signature[:-2]}AA"
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_token_expires(client, customer, clock):
    _, headers = customer
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    clock.advance(hours=71)
    assert client.get("/api/auth/me", headers=headers).status_code == 200  # still inside the 3 day test lifetime
    clock.advance(hours=2)
    expired = client.get("/api/auth/me", headers=headers)
    assert expired.status_code == 401
    assert expired.get_json()["error"]["code"] == "token_expired"


def test_only_an_admin_creates_staff(client, customer, agent, admin):
    body = {"email": "new@example.com", "name": "New Agent", "password": PASSWORD, "role": "agent"}
    assert client.post("/api/users", json=body, headers=customer[1]).status_code == 403
    assert client.post("/api/users", json=body, headers=agent[1]).status_code == 403
    created = client.post("/api/users", json=body, headers=admin[1])
    assert created.status_code == 201
    assert created.get_json()["role"] == "agent"

    bad_role = client.post("/api/users", json={**body, "email": "x@example.com", "role": "king"}, headers=admin[1])
    assert bad_role.status_code == 400


def test_staff_can_list_users_by_role(client, customer, agent, admin):
    agents = client.get("/api/users?role=agent", headers=admin[1]).get_json()["items"]
    assert [user["email"] for user in agents] == ["ann@example.com"]
    assert client.get("/api/users", headers=customer[1]).status_code == 403
    assert client.get("/api/users?role=king", headers=admin[1]).status_code == 400
    assert client.get("/api/users/9999", headers=admin[1]).status_code == 404
