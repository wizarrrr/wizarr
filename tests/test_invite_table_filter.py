"""
Regression test: the invite-table server filter must actually filter.

Selecting a server in the Invitations view posted the server id, but the handler
rebuilt the query without applying any filter — so every server showed all
invitations. The handler now restricts the query to invitations linked to the
selected server through the association table.
"""

from app.models import Invitation, MediaServer


def _servers(session, prefix):
    srv_a = MediaServer(
        name=f"{prefix} A", server_type="plex", url="http://a", api_key="ka"
    )
    srv_b = MediaServer(
        name=f"{prefix} B", server_type="jellyfin", url="http://b", api_key="kb"
    )
    session.add_all([srv_a, srv_b])
    session.commit()
    return srv_a, srv_b


def _table(client, server):
    response = client.post("/invite/table", data={"server": str(server.id)})
    assert response.status_code == 200
    return response.data.decode("utf-8")


def test_invite_table_filters_by_server(admin_client, session):
    """Filtering by a server returns only that server's invitations."""
    srv_a, srv_b = _servers(session, "Server")
    inv_a = Invitation(code="ONSERVERA", used=False, unlimited=False)
    inv_a.servers.append(srv_a)
    inv_b = Invitation(code="ONSERVERB", used=False, unlimited=False)
    inv_b.servers.append(srv_b)
    session.add_all([inv_a, inv_b])
    session.commit()

    body = _table(admin_client, srv_a)

    assert "ONSERVERA" in body
    assert "ONSERVERB" not in body


def test_invite_table_filter_includes_legacy_single_server_invite(
    admin_client, session
):
    """Legacy invites (server_id set, no association rows) still filter correctly.

    Older invitations predate the invitation_server association table and carry
    their server only on Invitation.server_id. The rest of the app treats such an
    invite as belonging to `invitation.server`, so the filter must surface it for
    that server and hide it for others.
    """
    srv_a, srv_b = _servers(session, "Legacy")
    # Legacy shape: server assigned via the single-server relationship only,
    # with no invitation_server association rows.
    session.add(Invitation(code="LEGACYONA", used=False, unlimited=False, server=srv_a))
    session.commit()

    assert "LEGACYONA" in _table(admin_client, srv_a)
    assert "LEGACYONA" not in _table(admin_client, srv_b)


def test_invite_table_filter_ignores_stale_legacy_server_id(admin_client, session):
    """A stale server_id must not broaden a genuine multi-server invite.

    An invite may carry both association rows (the authoritative multi-server
    truth) and a leftover legacy server_id pointing elsewhere. The legacy match
    must apply only when there are no association rows, so the stale id cannot
    make the invite appear under a server it is not actually linked to.
    """
    srv_a, srv_b = _servers(session, "Stale")
    # Linked to A via the association table, but with a stale legacy server_id
    # still pointing at B.
    inv = Invitation(code="STALEBID", used=False, unlimited=False, server=srv_b)
    inv.servers.append(srv_a)
    session.add(inv)
    session.commit()

    assert "STALEBID" in _table(admin_client, srv_a)
    assert "STALEBID" not in _table(admin_client, srv_b)
