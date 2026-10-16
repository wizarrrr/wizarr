def test_admin_login(client, admin_user):
    """POST /login authenticates an AdminAccount and redirects home."""
    resp = client.post(
        "/login", data={"username": "testadmin", "password": "TestPass123"}
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


def test_admin_login_rejects_a_wrong_password(client, admin_user):
    resp = client.post("/login", data={"username": "testadmin", "password": "Wrong"})
    assert resp.status_code == 200
    assert "Invalid username or password" in resp.get_data(as_text=True)


def test_head_login_does_not_log_auth_fail(client, caplog):
    """HEAD /login (used by uptime checks) must not be treated as a failed login attempt."""
    resp = client.head("/login")
    assert resp.status_code == 200
    assert "AUTH FAIL" not in caplog.text
