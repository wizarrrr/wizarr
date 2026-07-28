"""
Regression test: the invite-table server filter must actually filter.

Selecting a server in the Invitations view posted the server id, but the handler
rebuilt the query without applying any filter — so every server showed all
invitations. The handler now restricts the query to invitations linked to the
selected server through the association table.
"""

import pytest

from app.extensions import db
from app.models import AdminAccount, Invitation, MediaServer


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


def test_invite_table_filters_by_server(client, app, admin_user):
    """Filtering by a server returns only that server's invitations."""
    with app.app_context():
        srv_a = MediaServer(
            name="Server A", server_type="plex", url="http://a", api_key="ka"
        )
        srv_b = MediaServer(
            name="Server B", server_type="jellyfin", url="http://b", api_key="kb"
        )
        db.session.add_all([srv_a, srv_b])
        db.session.commit()

        inv_a = Invitation(code="ONSERVERA", used=False, unlimited=False)
        inv_a.servers.append(srv_a)
        inv_b = Invitation(code="ONSERVERB", used=False, unlimited=False)
        inv_b.servers.append(srv_b)
        db.session.add_all([inv_a, inv_b])
        db.session.commit()
        a_id = srv_a.id

    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

    response = client.post("/invite/table", data={"server": str(a_id)})
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "ONSERVERA" in body
    assert "ONSERVERB" not in body


def test_invite_table_filter_includes_legacy_single_server_invite(
    client, app, admin_user
):
    """Legacy invites (server_id set, no association rows) still filter correctly.

    Older invitations predate the invitation_server association table and carry
    their server only on Invitation.server_id. The rest of the app treats such an
    invite as belonging to `invitation.server`, so the filter must surface it for
    that server and hide it for others.
    """
    with app.app_context():
        srv_a = MediaServer(
            name="Legacy A", server_type="plex", url="http://la", api_key="kla"
        )
        srv_b = MediaServer(
            name="Legacy B", server_type="jellyfin", url="http://lb", api_key="klb"
        )
        db.session.add_all([srv_a, srv_b])
        db.session.commit()

        # Legacy shape: server assigned via the single-server relationship only,
        # with no invitation_server association rows.
        legacy = Invitation(code="LEGACYONA", used=False, unlimited=False, server=srv_a)
        db.session.add(legacy)
        db.session.commit()
        a_id, b_id = srv_a.id, srv_b.id

    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

    shown = client.post("/invite/table", data={"server": str(a_id)})
    assert shown.status_code == 200
    assert "LEGACYONA" in shown.data.decode("utf-8")

    hidden = client.post("/invite/table", data={"server": str(b_id)})
    assert hidden.status_code == 200
    assert "LEGACYONA" not in hidden.data.decode("utf-8")


def test_invite_table_filter_ignores_stale_legacy_server_id(client, app, admin_user):
    """A stale server_id must not broaden a genuine multi-server invite.

    An invite may carry both association rows (the authoritative multi-server
    truth) and a leftover legacy server_id pointing elsewhere. The legacy match
    must apply only when there are no association rows, so the stale id cannot
    make the invite appear under a server it is not actually linked to.
    """
    with app.app_context():
        srv_a = MediaServer(
            name="Stale A", server_type="plex", url="http://sa", api_key="ksa"
        )
        srv_b = MediaServer(
            name="Stale B", server_type="jellyfin", url="http://sb", api_key="ksb"
        )
        db.session.add_all([srv_a, srv_b])
        db.session.commit()

        # Linked to A via the association table, but with a stale legacy server_id
        # still pointing at B.
        inv = Invitation(code="STALEBID", used=False, unlimited=False, server=srv_b)
        inv.servers.append(srv_a)
        db.session.add(inv)
        db.session.commit()
        a_id, b_id = srv_a.id, srv_b.id

    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})

    on_a = client.post("/invite/table", data={"server": str(a_id)})
    assert on_a.status_code == 200
    assert "STALEBID" in on_a.data.decode("utf-8")

    on_b = client.post("/invite/table", data={"server": str(b_id)})
    assert on_b.status_code == 200
    assert "STALEBID" not in on_b.data.decode("utf-8")
