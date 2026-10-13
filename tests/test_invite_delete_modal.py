"""Tests for the invitation delete confirmation modal route."""

from app.models import Invitation


def _add_invite(session, code):
    invite = Invitation(code=code, used=False, unlimited=False)
    session.add(invite)
    session.commit()
    return invite.id


def test_delete_invite_modal_shows_invite_code(admin_client, session):
    """The modal renders the invitation's code so the admin can confirm it."""
    invite_id = _add_invite(session, "MODALTEST")

    response = admin_client.get(f"/invite/{invite_id}/delete-modal")

    assert response.status_code == 200
    assert b"MODALTEST" in response.data


def test_delete_invite_modal_requires_login(client, session):
    """Unauthenticated requests must not see the confirmation modal."""
    invite_id = _add_invite(session, "NOAUTH")

    response = client.get(f"/invite/{invite_id}/delete-modal")

    assert response.status_code == 302


def test_delete_invite_modal_404_for_missing_invite(admin_client):
    """A non-existent invite id returns 404 instead of a broken modal."""
    response = admin_client.get("/invite/999999/delete-modal")

    assert response.status_code == 404
