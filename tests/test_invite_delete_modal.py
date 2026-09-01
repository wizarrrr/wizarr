"""Tests for the invitation delete confirmation modal route."""

import pytest

from app.extensions import db
from app.models import AdminAccount, Invitation


@pytest.fixture
def admin_user(app):
    """Create an admin account for authenticated requests."""
    with app.app_context():
        created = False
        previous_hash = None
        admin = AdminAccount.query.filter_by(username="testadmin").first()
        if not admin:
            admin = AdminAccount(username="testadmin")
            admin.set_password("TestPass123")
            db.session.add(admin)
            db.session.commit()
            created = True
        else:
            previous_hash = admin.password_hash
            admin.set_password("TestPass123")
            db.session.commit()
        yield admin
        if created:
            db.session.delete(admin)
            db.session.commit()
        elif previous_hash is not None:
            admin = AdminAccount.query.filter_by(username="testadmin").first()
            if admin:
                admin.password_hash = previous_hash
                db.session.commit()


def test_delete_invite_modal_shows_invite_code(client, app, admin_user):
    """The modal renders the invitation's code so the admin can confirm it."""
    with app.app_context():
        invite = Invitation(code="MODALTEST", used=False, unlimited=False)
        db.session.add(invite)
        db.session.commit()
        invite_id = invite.id

    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

    response = client.get(f"/invite/{invite_id}/delete-modal")

    assert response.status_code == 200
    assert b"MODALTEST" in response.data


def test_delete_invite_modal_requires_login(client, app):
    """Unauthenticated requests must not see the confirmation modal."""
    with app.app_context():
        invite = Invitation(code="NOAUTH", used=False, unlimited=False)
        db.session.add(invite)
        db.session.commit()
        invite_id = invite.id

    response = client.get(f"/invite/{invite_id}/delete-modal")

    assert response.status_code in (302, 401)


def test_delete_invite_modal_404_for_missing_invite(client, app, admin_user):
    """A non-existent invite id returns 404 instead of a broken modal."""
    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

    response = client.get("/invite/999999/delete-modal")

    assert response.status_code == 404
