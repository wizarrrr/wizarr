"""
After a join, the invitation records which user used it on which server. On
an unlimited invite several people share the code, so the lookup must find
the person who just joined, not whoever joined first.
"""

from app.extensions import db
from app.models import Invitation, MediaServer, User, invitation_users
from app.services.invitation_manager import InvitationManager


class JoiningClient:
    """Creates the local user the way a real client's join does."""

    def __init__(self, server):
        self.server = server

    def join(self, username, password, confirm, email, code):
        db.session.add(
            User(
                username=username,
                email=email,
                token=username,
                code=code,
                server_id=self.server.id,
            )
        )
        db.session.commit()
        return True, ""


def _unlimited_invite():
    server = MediaServer(
        name="J", server_type="jellyfin", url="http://j.local", api_key="k"
    )
    invitation = Invitation(code="SHARED0001", used=False, unlimited=True)
    invitation.servers.append(server)
    db.session.add_all([server, invitation])
    db.session.commit()
    return server, invitation


def test_each_person_on_an_unlimited_invite_is_recorded(session, monkeypatch):
    server, invitation = _unlimited_invite()
    monkeypatch.setattr(
        "app.services.invitation_manager.get_client_for_media_server", JoiningClient
    )

    for name in ("first", "second"):
        ok, _code, errors = InvitationManager.process_invitation(
            "SHARED0001", name, "Password1", "Password1", f"{name}@example.com"
        )
        assert ok, errors

    rows = db.session.execute(
        invitation_users.select().where(invitation_users.c.invite_id == invitation.id)
    )
    recorded = {
        user.username for row in rows if (user := db.session.get(User, row.user_id))
    }
    assert recorded == {"first", "second"}


def test_find_joined_user_matches_username_or_email(session):
    from app.services.invites import find_joined_user

    server, _invitation = _unlimited_invite()
    for name in ("first", "second"):
        db.session.add(
            User(
                username=name,
                email=f"{name}@example.com",
                token=name,
                code="SHARED0001",
                server_id=server.id,
            )
        )
    db.session.commit()

    by_email = find_joined_user("SHARED0001", server.id, email="first@example.com")
    by_name = find_joined_user("SHARED0001", server.id, username="second")
    assert by_email is not None and by_email.username == "first"
    assert by_name is not None and by_name.username == "second"
    assert find_joined_user("SHARED0001", server.id, email="x@example.com") is None
