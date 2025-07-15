from app.extensions import db
from app.models import AdminAccount


def test_admin_account_crud(app):
    """Creating an admin account persists and password hashing works."""
    with app.app_context():
        acc = AdminAccount(username="alice")
        acc.set_password("Secret123")
        db.session.add(acc)
        db.session.commit()

        fetched = AdminAccount.query.filter_by(username="alice").first()
        assert fetched is not None
        assert fetched.check_password("Secret123")
        assert not fetched.check_password("WrongPass")


def test_admin_login(client, app):
    """POST /login authenticates an AdminAccount and redirects home."""
    with app.app_context():
        acc = AdminAccount(username="bob")
        acc.set_password("Password1")
        db.session.add(acc)
        db.session.commit()

    resp = client.post("/login", data={"username": "bob", "password": "Password1"})
    # Should redirect to / on success (302 Found)
    assert resp.status_code in {302, 303}
    assert resp.headers["Location"].endswith("/")
