"""
Regression test: invitations must be deletable by primary key.

Deleting by ``code`` broke when a code contained a trailing space. The browser
strips trailing spaces from the query string, so the exact-match lookup never
matched the stored code and the invitation became impossible to delete from the
UI (it appeared to "respawn" after every delete). The delete action now uses the
invitation id, and ``create_invite`` strips surrounding whitespace so such codes
can't be stored in the first place.
"""

import pytest

from app.extensions import db
from app.models import AdminAccount, Invitation, MediaServer
from app.services.invites import create_invite


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


def test_delete_invite_with_trailing_space_in_code(client, app, admin_user):
    """An invite whose code has a trailing space is deletable via its id."""
    with app.app_context():
        invite = Invitation(code="ABC123 ", used=False, unlimited=False)
        db.session.add(invite)
        db.session.commit()
        invite_id = invite.id

    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

    response = client.post(f"/invite/table?delete_id={invite_id}")
    assert response.status_code == 200

    with app.app_context():
        assert db.session.get(Invitation, invite_id) is None


def test_stale_delete_by_code_param_is_ignored(client, app, admin_user):
    """A cached ?delete= request (old code-based contract) must not delete a row.

    The delete action moved to an explicit ?delete_id= parameter. Old cached
    markup can still post ?delete=<code>, where the code may be numeric and
    collide with an unrelated invitation's id. Such requests must now no-op so
    they can never delete the wrong invitation.
    """
    with app.app_context():
        invite = Invitation(code="123", used=False, unlimited=False)
        db.session.add(invite)
        db.session.commit()
        invite_id = invite.id

    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

    # Old contract: ?delete=<numeric code that happens to equal a real id>.
    response = client.post(f"/invite/table?delete={invite_id}")
    assert response.status_code == 200

    with app.app_context():
        # Still present — the legacy parameter no longer deletes anything.
        assert db.session.get(Invitation, invite_id) is not None


@pytest.mark.parametrize("bad_id", ["²", "abc", "9" * 5000, "", "1.5", "-"])
def test_delete_with_unparseable_id_is_noop_not_500(client, app, admin_user, bad_id):
    """Non-integer delete_id values must no-op with 200, never raise a 500.

    str.isdigit() accepts values int() rejects ("²"), and digit strings longer
    than Python's conversion limit raise ValueError. The handler parses in a
    try/except and treats anything unparseable as a no-op.
    """
    with app.app_context():
        invite = Invitation(code="KEEPME", used=False, unlimited=False)
        db.session.add(invite)
        db.session.commit()
        invite_id = invite.id

    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

    response = client.post(f"/invite/table?delete_id={bad_id}")
    assert response.status_code == 200

    with app.app_context():
        assert db.session.get(Invitation, invite_id) is not None


def test_create_invite_strips_whitespace_from_code(app):
    """create_invite() strips surrounding whitespace before storing the code."""
    with app.app_context():
        server = MediaServer(
            name="Strip Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        db.session.add(server)
        db.session.flush()

        invite = create_invite(
            {"code": "STRIP01 ", "expires": "never", "server_ids": [str(server.id)]}
        )
        assert invite.code == "STRIP01"
