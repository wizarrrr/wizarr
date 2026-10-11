import re
from unittest.mock import Mock, patch

import pytest

from app.models import Invitation, MediaServer


def _create_jellyfin_invitation(session):
    server = MediaServer(
        name="Test Jellyfin",
        server_type="jellyfin",
        url="http://jellyfin.example.com",
        api_key="test-key",
    )
    invitation = Invitation(code="ERR123", unlimited=True, used=False)

    session.add(server)
    session.add(invitation)
    session.flush()
    invitation.servers.append(server)
    session.commit()

    return server, invitation


@pytest.mark.parametrize(
    "join_error",
    [
        "Invalid e-mail address.",
        "User or e-mail already exists.",
    ],
)
def test_invitation_process_rerenders_open_join_form_on_email_error(
    client, session, join_error
):
    _create_jellyfin_invitation(session)
    media_client = Mock()
    media_client.join.return_value = (False, join_error)

    with patch(
        "app.services.invitation_flow.workflows.get_client_for_media_server",
        return_value=media_client,
    ):
        response = client.post(
            "/invitation/process",
            data={
                "code": "ERR123",
                "username": "validuser",
                "email": "user@example.com",
                "password": "ValidPass1",
                "confirm_password": "ValidPass1",
            },
        )

    body = response.data
    form_screen = re.search(rb'<div class="[^"]*"[^>]*id="form-screen"', body)

    assert response.status_code == 200
    assert join_error.encode() in body
    assert b"Test Jellyfin" in body
    assert b"--color-primary: #AA5CC3;" in body
    assert form_screen is not None
    assert b"opacity-100" in form_screen.group(0)
    assert b"hidden" not in form_screen.group(0)
