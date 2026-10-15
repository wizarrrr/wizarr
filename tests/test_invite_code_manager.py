"""Unit tests for InviteCodeManager: session storage and code validation."""

import datetime
from datetime import timedelta

import pytest
from flask import session as flask_session

from app.models import Invitation, MediaServer
from app.services.invite_code_manager import InviteCodeManager


@pytest.fixture
def request_context(app):
    with app.test_request_context():
        yield


class TestSessionData:
    def test_store_and_get_invite_code(self, request_context):
        assert InviteCodeManager.get_invite_code() is None

        InviteCodeManager.store_invite_code("FIRST123")
        InviteCodeManager.store_invite_code("SECOND123")

        assert InviteCodeManager.get_invite_code() == "SECOND123"

    def test_pre_wizard_complete_flag(self, request_context):
        assert InviteCodeManager.is_pre_wizard_complete() is False

        InviteCodeManager.mark_pre_wizard_complete()

        assert InviteCodeManager.is_pre_wizard_complete() is True

    def test_storing_the_same_code_keeps_the_completion_flag(self, request_context):
        InviteCodeManager.store_invite_code("CODE123")
        InviteCodeManager.mark_pre_wizard_complete()

        InviteCodeManager.store_invite_code("CODE123")

        assert InviteCodeManager.is_pre_wizard_complete() is True

    def test_storing_a_new_code_resets_the_completion_flag(self, request_context):
        InviteCodeManager.store_invite_code("FIRST123")
        InviteCodeManager.mark_pre_wizard_complete()

        InviteCodeManager.store_invite_code("SECOND123")

        assert InviteCodeManager.is_pre_wizard_complete() is False

    def test_clear_invite_data(self, request_context):
        InviteCodeManager.store_invite_code("CODE123")
        InviteCodeManager.mark_pre_wizard_complete()

        InviteCodeManager.clear_invite_data()

        assert InviteCodeManager.STORAGE_KEY not in flask_session
        assert InviteCodeManager.PRE_WIZARD_COMPLETE_KEY not in flask_session

    def test_clear_invite_data_when_empty(self, request_context):
        InviteCodeManager.clear_invite_data()

        assert InviteCodeManager.get_invite_code() is None
        assert InviteCodeManager.is_pre_wizard_complete() is False


class TestInviteCodeValidation:
    def test_validate_valid_invitation(self, session):
        server = MediaServer(
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        invitation = Invitation(
            code="VALID123",
            unlimited=True,
            used=False,
            expires=datetime.datetime.now(datetime.UTC) + timedelta(days=7),
        )
        invitation.servers.append(server)
        session.add(invitation)
        session.commit()

        is_valid, inv = InviteCodeManager.validate_invite_code("VALID123")

        assert is_valid is True
        assert inv is not None
        assert inv.code == "VALID123"

    def test_validate_case_insensitive(self, session):
        session.add(Invitation(code="UPPER123", unlimited=True, used=False))
        session.commit()

        is_valid, inv = InviteCodeManager.validate_invite_code("upper123")

        assert is_valid is True
        assert inv is not None
        assert inv.code == "UPPER123"

    def test_validate_used_unlimited_invitation(self, session):
        session.add(Invitation(code="UNLIMITED123", unlimited=True, used=True))
        session.commit()

        is_valid, inv = InviteCodeManager.validate_invite_code("UNLIMITED123")

        assert is_valid is True
        assert inv is not None

    @pytest.mark.parametrize(
        "code",
        ["EXPIRED123", "USED123", "NOTEXIST123", "", None],
        ids=["expired", "used-limited", "unknown", "empty", "none"],
    )
    def test_validate_rejects(self, session, code):
        session.add_all(
            [
                Invitation(
                    code="EXPIRED123",
                    unlimited=False,
                    used=False,
                    expires=datetime.datetime.now(datetime.UTC) - timedelta(hours=1),
                ),
                Invitation(code="USED123", unlimited=False, used=True),
            ]
        )
        session.commit()

        assert InviteCodeManager.validate_invite_code(code) == (False, None)
