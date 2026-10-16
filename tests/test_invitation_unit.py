"""Unit tests for invitation validation, creation, and usage tracking."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models import Invitation, Library, MediaServer, User
from app.services.invites import create_invite, is_invite_valid, mark_server_used


def _server(session, name="Test Server", server_type="jellyfin"):
    server = MediaServer(
        name=name,
        server_type=server_type,
        url="http://localhost:8096",
        api_key="test-key",
    )
    session.add(server)
    session.flush()
    return server


def _user(session, invite, server):
    user = User(
        username="testuser",
        email="test@example.com",
        token="user-token",
        code=invite.code,
        server_id=server.id,
    )
    session.add(user)
    session.commit()
    return user


class TestInvitationValidation:
    def test_valid_invitation_basic(self, session):
        server = _server(session)
        invite = create_invite(
            {"expires": "month", "unlimited": False, "server_ids": [str(server.id)]}
        )

        assert is_invite_valid(invite.code) == (True, "okay")

    @pytest.mark.parametrize(
        ("invite", "code", "expected"),
        [
            (
                {"expires": datetime.now(UTC) - timedelta(hours=1)},
                "EXPIRED12",
                (False, "Invitation has expired."),
            ),
            (
                {"used": True, "unlimited": False},
                "USED123",
                (False, "Invitation has already been used."),
            ),
            ({"used": True, "unlimited": True}, "UNLIMIT123", (True, "okay")),
            (None, "AB", (False, "Invalid code length")),
            (None, "A" * 50, (False, "Invalid code length")),
            (None, "NOTEXIST12", (False, "Invalid code")),
        ],
        ids=["expired", "used-limited", "used-unlimited", "short", "long", "unknown"],
    )
    def test_invite_state(self, session, invite, code, expected):
        if invite is not None:
            session.add(Invitation(code=code, **invite))
            session.commit()

        assert is_invite_valid(code) == expected


class TestInvitationCreation:
    def test_create_basic_invitation(self, session):
        server = _server(session)

        invite = create_invite(
            {
                "expires": "week",
                "unlimited": True,
                "server_ids": [str(server.id)],
                "duration": "14",
            }
        )

        assert invite.code is not None
        assert len(invite.code) >= 3
        assert invite.unlimited is True
        assert invite.duration == "14"
        assert invite.expires is not None
        assert list(invite.servers) == [server]  # type: ignore

    def test_create_invitation_with_libraries(self, session):
        server = _server(session)
        lib1 = Library(
            name="Movies", external_id="lib1", server_id=server.id, enabled=True
        )
        lib2 = Library(
            name="TV Shows", external_id="lib2", server_id=server.id, enabled=True
        )
        session.add_all([lib1, lib2])
        session.flush()

        invite = create_invite(
            {
                "expires": "month",
                "unlimited": False,
                "server_ids": [str(server.id)],
                "libraries": [str(lib1.id), str(lib2.id)],
            }
        )

        assert {lib.id for lib in invite.libraries} == {lib1.id, lib2.id}  # type: ignore

    def test_create_multi_server_invitation(self, session):
        server1 = _server(session, "Jellyfin Server", "jellyfin")
        server2 = _server(session, "Plex Server", "plex")

        invite = create_invite(
            {
                "expires": "never",
                "unlimited": False,
                "server_ids": [str(server1.id), str(server2.id)],
            }
        )

        assert {server.id for server in invite.servers} == {server1.id, server2.id}  # type: ignore

    def test_create_invitation_validation_errors(self, session):
        with pytest.raises(ValueError, match="At least one server must be selected"):
            create_invite({"expires": "month", "unlimited": False, "server_ids": []})

    def test_create_invitation_with_custom_code(self, session):
        server = _server(session)

        invite = create_invite(
            {
                "code": "CUSTOM123",
                "expires": "month",
                "unlimited": False,
                "server_ids": [str(server.id)],
            }
        )

        assert invite.code == "CUSTOM123"


class TestInvitationMarkingUsed:
    def test_mark_unlimited_invitation_used(self, session):
        server = _server(session)
        invite = create_invite(
            {"expires": "month", "unlimited": True, "server_ids": [str(server.id)]}
        )
        user = _user(session, invite, server)
        assert invite.used is False

        mark_server_used(invite, server.id, user)

        # The admin pages show an unlimited invite as used after the first join,
        # but the invite stays valid.
        session.refresh(invite)
        assert invite.used is True
        assert invite.used_by == user
        assert is_invite_valid(invite.code)[0]

    def test_mark_limited_single_server_used(self, session):
        server = _server(session)
        invite = create_invite(
            {"expires": "month", "unlimited": False, "server_ids": [str(server.id)]}
        )
        user = _user(session, invite, server)

        mark_server_used(invite, server.id, user)

        session.refresh(invite)
        assert invite.used is True
        assert invite.used_by == user
        assert user in invite.users  # type: ignore
        assert is_invite_valid(invite.code) == (
            False,
            "Invitation has already been used.",
        )
