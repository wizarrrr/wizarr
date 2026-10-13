"""Creating an invite with the library picker opened but every box cleared is
rejected, replacing the silent "unchecked all -> grant every enabled library"
surprise with an explicit error. An invite whose picker was never opened is
unaffected and still falls back to all enabled libraries at redeem time.
"""

import pytest

from app.models import Invitation, Library, MediaServer

# /invite is an HTMX-only endpoint (it redirects to the dashboard otherwise).
HX = {"HX-Request": "true", "HX-Current-URL": "http://localhost/admin/invites"}


def _server(session, name="Plex"):
    server = MediaServer(
        name=name, server_type="plex", url="http://plex.local", api_key="token"
    )
    session.add(server)
    session.commit()
    return server


def _library(session, server):
    lib = Library(external_id="1", name="Movies", server_id=server.id, enabled=True)
    session.add(lib)
    session.commit()
    return lib


def _create_invite(client, server, **data):
    return client.post(
        "/invite",
        data={"server_ids": str(server.id), "expires": "never", **data},
        headers=HX,
    )


@pytest.mark.parametrize(
    "libraries",
    [
        # Marker present and zero boxes checked.
        lambda session: None,
        # A stale or deleted ID resolves to zero eligible libraries. Without
        # the check the invite has no library rows, and redemption falls back
        # to every enabled library.
        lambda session: "999999",
        # An ID from a server that is not part of this invite must not resolve
        # to zero libraries and slip through as an unscoped invite.
        lambda session: str(_library(session, _server(session, "Other Plex")).id),
    ],
    ids=["cleared", "stale-id", "other-server-library"],
)
def test_picker_used_without_an_eligible_library_is_rejected(
    admin_client, session, libraries
):
    server = _server(session)
    data = {"library_picker_used": "1"}
    if (library_ids := libraries(session)) is not None:
        data["libraries"] = library_ids

    resp = _create_invite(admin_client, server, **data)

    assert resp.status_code == 400
    assert b"at least one library" in resp.data
    assert Invitation.query.count() == 0


def test_picker_with_a_selection_is_created(admin_client, session):
    """Marker present + a library kept -> invite created with exactly that library."""
    server = _server(session)
    lib = _library(session, server)

    resp = _create_invite(
        admin_client, server, library_picker_used="1", libraries=str(lib.id)
    )

    assert resp.status_code == 200
    inv = Invitation.query.one()
    assert [library.id for library in inv.libraries] == [lib.id]


def test_untouched_picker_is_allowed(admin_client, session):
    """No marker (picker never opened) -> allowed; redeem-time fallback still applies."""
    server = _server(session)

    resp = _create_invite(admin_client, server)

    assert resp.status_code == 200
    inv = Invitation.query.one()
    assert list(inv.libraries) == []
