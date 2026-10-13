"""Tests for the invitation flow manager, workflows, and strategies."""

from unittest.mock import Mock, patch

import pytest
from flask import render_template
from flask import session as flask_session

from app.models import Invitation, MediaServer
from app.services.invitation_flow import InvitationFlowManager
from app.services.invitation_flow.results import ProcessingStatus
from app.services.invitation_flow.strategies import (
    FormBasedStrategy,
    HybridStrategy,
    PlexOAuthStrategy,
    StrategyFactory,
)
from app.services.invitation_flow.workflows import (
    FormBasedWorkflow,
    MixedWorkflow,
    PlexOAuthWorkflow,
    WorkflowFactory,
)


class TestInvitationFlowManager:
    @patch("app.services.invitation_flow.manager.is_invite_valid")
    def test_process_invitation_display_invalid(self, mock_is_valid):
        mock_is_valid.return_value = (False, "Invalid invitation")

        manager = InvitationFlowManager()
        result = manager.process_invitation_display("INVALID")

        assert result.status == ProcessingStatus.INVALID_INVITATION
        assert result.message == "Invalid invitation"
        assert result.template_data is not None
        assert result.template_data["template_name"] == "invalid-invite.html"

    def test_get_invitation_servers_no_servers(self):
        invitation = Mock(servers=[], server=None)

        with patch("app.services.invitation_flow.manager.MediaServer") as media_server:
            media_server.query.first.return_value = None

            assert InvitationFlowManager()._get_invitation_servers(invitation) == []

    def test_get_invitation_servers_puts_plex_first(self):
        jellyfin = Mock(server_type="jellyfin")
        plex = Mock(server_type="plex")
        invitation = Mock(servers=[jellyfin, plex], server=None)

        servers = InvitationFlowManager()._get_invitation_servers(invitation)

        assert servers == [plex, jellyfin]


@pytest.mark.parametrize(
    ("server_types", "workflow_cls", "strategy_cls"),
    [
        ([], FormBasedWorkflow, FormBasedStrategy),
        (["jellyfin"], FormBasedWorkflow, FormBasedStrategy),
        (["plex"], PlexOAuthWorkflow, PlexOAuthStrategy),
        (["plex", "jellyfin"], MixedWorkflow, HybridStrategy),
    ],
)
def test_factories_choose_by_server_types(server_types, workflow_cls, strategy_cls):
    servers = [Mock(server_type=server_type) for server_type in server_types]

    assert isinstance(WorkflowFactory.create_workflow(servers), workflow_cls)
    assert isinstance(StrategyFactory.create_strategy(servers), strategy_cls)


class TestFormBasedStrategy:
    def test_authenticate_success(self):
        strategy = FormBasedStrategy()
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
        }

        success, message, user_data = strategy.authenticate([], form_data)

        assert success is True
        assert message == "Form authentication successful"
        assert user_data["username"] == "testuser"

    def test_authenticate_missing_field(self):
        strategy = FormBasedStrategy()
        form_data = {
            "email": "test@example.com",
            "password": "testpass123",
            "confirm_password": "testpass123",
        }

        success, message, user_data = strategy.authenticate([], form_data)

        assert success is False
        assert "Missing required field: username" in message

    def test_authenticate_password_mismatch(self):
        strategy = FormBasedStrategy()
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "confirm_password": "different",
        }

        success, message, user_data = strategy.authenticate([], form_data)

        assert success is False
        assert "Passwords do not match" in message

    def test_get_required_fields(self):
        strategy = FormBasedStrategy()
        fields = strategy.get_required_fields()

        assert "username" in fields
        assert "email" in fields
        assert "password" in fields
        assert "confirm_password" in fields


class TestPlexOAuthStrategy:
    def test_authenticate_with_token(self):
        strategy = PlexOAuthStrategy()
        form_data = {"oauth_token": "test_token_123"}

        success, message, user_data = strategy.authenticate([], form_data)

        assert success is True
        assert message == "Plex OAuth authentication successful"
        assert user_data["plex_token"] == "test_token_123"

    def test_authenticate_missing_token(self, app):
        strategy = PlexOAuthStrategy()
        form_data = {}

        with app.test_request_context():
            success, message, user_data = strategy.authenticate([], form_data)

            assert success is False
            assert "OAuth token required" in message

    def test_get_required_fields(self):
        strategy = PlexOAuthStrategy()
        fields = strategy.get_required_fields()

        assert fields == []  # OAuth doesn't need form fields


class TestFormBasedWorkflow:
    def test_show_initial_form(self, app):
        workflow = FormBasedWorkflow()

        mock_invitation = Mock()
        mock_invitation.code = "TEST123"

        mock_server = Mock()
        mock_server.server_type = "jellyfin"

        with app.app_context():
            result = workflow.show_initial_form(mock_invitation, [mock_server])

            assert result.status == ProcessingStatus.AUTHENTICATION_REQUIRED
            assert result.template_data is not None
            assert result.template_data["template_name"] == "welcome-jellyfin.html"

    @patch("app.services.invitation_flow.workflows.StrategyFactory")
    def test_process_submission_success(self, mock_strategy_factory, app):
        workflow = FormBasedWorkflow()

        # Mock strategy
        mock_strategy = Mock()
        mock_strategy.authenticate.return_value = (
            True,
            "Success",
            {"username": "test"},
        )
        mock_strategy_factory.create_strategy.return_value = mock_strategy

        # Mock invitation
        mock_invitation = Mock()
        mock_invitation.code = "TEST123"
        mock_invitation.wizard_bundle_id = None

        # Mock server processing
        with patch.object(workflow, "_process_servers") as mock_process:
            mock_server_result = Mock()
            mock_server_result.server.name = "Test Server"
            mock_server_result.message = "Success"
            mock_process.return_value = ([mock_server_result], [])

            with app.test_request_context():
                result = workflow.process_submission(
                    mock_invitation,
                    [],
                    {
                        "code": "TEST123",
                        "username": "testuser",
                        "email": "test@example.com",
                        "password": "Testpass123",
                        "confirm_password": "Testpass123",
                    },
                )

                assert result.status == ProcessingStatus.SUCCESS
                assert result.redirect_url == "/wizard/"

    @patch("app.services.invitation_flow.workflows.StrategyFactory")
    def test_process_submission_rejects_invalid_username(
        self, mock_strategy_factory, app
    ):
        workflow = FormBasedWorkflow()

        mock_invitation = Mock()
        mock_invitation.code = "TEST123"

        with (
            patch.object(workflow, "_process_servers") as mock_process,
            app.test_request_context(),
        ):
            result = workflow.process_submission(
                mock_invitation,
                [],
                {
                    "code": "TEST123",
                    "username": "ab",
                    "email": "test@example.com",
                    "password": "Testpass123",
                    "confirm_password": "Testpass123",
                },
            )

            assert result.status == ProcessingStatus.FAILURE
            assert result.template_data is not None
            assert result.template_data["template_name"] == "welcome-jellyfin.html"
            assert result.template_data["form"].username.errors

        mock_strategy_factory.create_strategy.assert_not_called()
        mock_process.assert_not_called()


class TestMixedWorkflow:
    def test_show_local_password_form_preserves_invite_code(self, app):
        workflow = MixedWorkflow()

        mock_invitation = Mock()
        mock_invitation.code = "MIXED123"

        mock_plex_server = Mock()
        mock_plex_server.server_type = "plex"
        mock_local_server = Mock()
        mock_local_server.server_type = "jellyfin"
        mock_local_server.name = "Local Server"

        with app.test_request_context():
            flask_session["plex_oauth_token"] = "plex-token"

            result = workflow.show_initial_form(
                mock_invitation, [mock_plex_server, mock_local_server]
            )

            assert result.status == ProcessingStatus.AUTHENTICATION_REQUIRED
            assert result.template_data is not None
            assert result.template_data["template_name"] == "hybrid-password-form.html"
            assert result.template_data["form"].code.data == "MIXED123"

            rendered = render_template(
                result.template_data["template_name"], **result.template_data
            )

            assert 'name="code"' in rendered
            assert 'value="MIXED123"' in rendered


def _invitation(session, code, server_type):
    server = MediaServer(
        name="Test Server",
        server_type=server_type,
        url="http://test.example.com",
        api_key="test_key",
    )
    invitation = Invitation(code=code, used=False, unlimited=False)
    invitation.servers.append(server)
    session.add(invitation)
    session.commit()


class TestEndToEndFlow:
    @patch("app.services.invitation_flow.manager.is_invite_valid")
    @patch("app.services.invitation_flow.workflows.get_client_for_media_server")
    def test_complete_jellyfin_flow(self, mock_get_client, mock_is_valid, app, session):
        mock_is_valid.return_value = (True, "Valid invitation")
        mock_client = Mock()
        mock_client.join.return_value = (True, "User created successfully")
        mock_get_client.return_value = mock_client
        _invitation(session, "E2E123", "jellyfin")

        with app.test_request_context():
            manager = InvitationFlowManager()
            display_result = manager.process_invitation_display("E2E123")

            assert display_result.status == ProcessingStatus.AUTHENTICATION_REQUIRED
            assert display_result.template_data is not None
            assert (
                display_result.template_data["template_name"] == "welcome-jellyfin.html"
            )

            submission_result = manager.process_invitation_submission(
                {
                    "code": "E2E123",
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "Testpass123",
                    "confirm_password": "Testpass123",
                }
            )

            assert submission_result.status == ProcessingStatus.SUCCESS
            assert submission_result.redirect_url == "/wizard/"

    @patch("app.services.invitation_flow.manager.is_invite_valid")
    def test_complete_plex_flow(self, mock_is_valid, app, session):
        mock_is_valid.return_value = (True, "Valid invitation")
        _invitation(session, "PLEX123", "plex")

        with app.test_request_context():
            display_result = InvitationFlowManager().process_invitation_display(
                "PLEX123"
            )

            assert display_result.status == ProcessingStatus.OAUTH_PENDING
            assert display_result.template_data is not None
            assert (
                display_result.template_data["template_name"] == "user-plex-login.html"
            )
