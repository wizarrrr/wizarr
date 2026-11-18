"""Creating an invite with an optional recipient email sends the invite link
by email right after creation. A send failure must not fail invite creation;
it surfaces as a non-blocking warning in the response instead.
"""

from unittest.mock import patch

from app.models import Invitation, MediaServer
from app.services.email import EmailSendError

# /invite is an HTMX-only endpoint (it redirects to the dashboard otherwise).
HX = {"HX-Request": "true", "HX-Current-URL": "http://localhost/admin/invites"}


def _server(session, name="Plex"):
    server = MediaServer(
        name=name, server_type="plex", url="http://plex.local", api_key="token"
    )
    session.add(server)
    session.commit()
    return server


def _create_invite(client, server, **data):
    return client.post(
        "/invite",
        data={"server_ids": str(server.id), "expires": "never", **data},
        headers=HX,
    )


def test_recipient_email_sends_the_invite_link(admin_client, session):
    server = _server(session)

    with patch("app.services.email.send_invite_email") as send:
        resp = _create_invite(
            admin_client, server, recipient_email="friend@example.com"
        )

    assert resp.status_code == 200
    inv = Invitation.query.one()
    send.assert_called_once()
    args, _kwargs = send.call_args
    assert args[0] == "friend@example.com"
    assert f"/j/{inv.code}" in args[1]
    assert b"could not be sent" not in resp.data


def test_send_failure_does_not_fail_invite_creation(admin_client, session):
    server = _server(session)

    with patch(
        "app.services.email.send_invite_email",
        side_effect=EmailSendError("SMTP is not configured or not enabled"),
    ):
        resp = _create_invite(
            admin_client, server, recipient_email="friend@example.com"
        )

    assert resp.status_code == 200
    assert Invitation.query.count() == 1
    assert b"could not be sent" in resp.data


def test_no_recipient_email_does_not_send(admin_client, session):
    server = _server(session)

    with patch("app.services.email.send_invite_email") as send:
        resp = _create_invite(admin_client, server)

    assert resp.status_code == 200
    send.assert_not_called()
