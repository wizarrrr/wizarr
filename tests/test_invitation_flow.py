"""
Working tests for the invitation flow system
"""

from unittest.mock import Mock, patch

from app.extensions import db
from app.models import Invitation, MediaServer
from app.services.invitation_flow import InvitationFlowManager
from app.services.invitation_flow.results import ProcessingStatus
from app.services.invitation_flow.server_registry import (
    FormBasedAccountManager,
    PlexAccountManager,
    ServerIntegrationRegistry,
)
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
    """Test the InvitationFlowManager class"""

    def test_manager_initialization(self):
        """Test manager can be initialized"""
        manager = InvitationFlowManager()
        assert manager is not None
        assert hasattr(manager, "logger")

    @patch("app.services.invitation_flow.manager.is_invite_valid")
    def test_process_invitation_display_invalid(self, mock_is_valid):
        """Test display with invalid invitation"""
        mock_is_valid.return_value = (False, "Invalid invitation")

        manager = InvitationFlowManager()
        result = manager.process_invitation_display("INVALID")

        assert result.status == ProcessingStatus.INVALID_INVITATION
        assert result.message == "Invalid invitation"
        assert result.template_data is not None
        assert result.template_data["template_name"] == "invalid-invite.html"

    @patch("app.services.invitation_flow.manager.is_invite_valid")
    @patch("app.services.invitation_flow.manager.Invitation")
    def test_process_invitation_display_valid(
        self, mock_invitation_model, mock_is_valid, app
    ):
        """Test display with valid invitation"""
        mock_is_valid.return_value = (True, "Valid invitation")

        # Mock invitation
        mock_invitation = Mock()
        mock_invitation.code = "TEST123"
        mock_invitation.servers = []
        mock_invitation.server = None

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_invitation
        mock_invitation_model.query = mock_query

        # Mock MediaServer query
        with patch(
            "app.services.invitation_flow.manager.MediaServer"
        ) as mock_media_server:
            mock_server = Mock()
            mock_server.server_type = "jellyfin"
            mock_media_server.query.first.return_value = mock_server

            with app.app_context():
                manager = InvitationFlowManager()
                result = manager.process_invitation_display("TEST123")

                assert result.status in [
                    ProcessingStatus.AUTHENTICATION_REQUIRED,
                    ProcessingStatus.OAUTH_PENDING,
                ]

    def test_get_invitation_servers_no_servers(self):
        """Test getting servers when none exist"""
        manager = InvitationFlowManager()

        mock_invitation = Mock()
        mock_invitation.servers = []
        mock_invitation.server = None

        with patch(
            "app.services.invitation_flow.manager.MediaServer"
        ) as mock_media_server:
            mock_media_server.query.first.return_value = None

            servers = manager._get_invitation_servers(mock_invitation)
            assert servers == []

    def test_get_invitation_servers_with_servers(self):
        """Test getting servers with servers relation"""
        manager = InvitationFlowManager()

        mock_server1 = Mock()
        mock_server1.server_type = "plex"
        mock_server2 = Mock()
        mock_server2.server_type = "jellyfin"

        mock_invitation = Mock()
        mock_invitation.servers = [mock_server1, mock_server2]
        mock_invitation.server = None

        servers = manager._get_invitation_servers(mock_invitation)
        assert len(servers) == 2
        # Plex should be first
        assert servers[0].server_type == "plex"


class TestWorkflowFactory:
    """Test WorkflowFactory"""

    def test_create_workflow_no_servers(self):
        """Test creating workflow with no servers"""
        workflow = WorkflowFactory.create_workflow([])
        assert isinstance(workflow, FormBasedWorkflow)

    def test_create_workflow_jellyfin_only(self):
        """Test creating workflow with Jellyfin only"""
        mock_server = Mock()
        mock_server.server_type = "jellyfin"

        workflow = WorkflowFactory.create_workflow([mock_server])
        assert isinstance(workflow, FormBasedWorkflow)

    def test_create_workflow_plex_only(self):
        """Test creating workflow with Plex only"""
        mock_server = Mock()
        mock_server.server_type = "plex"

        workflow = WorkflowFactory.create_workflow([mock_server])
        assert isinstance(workflow, PlexOAuthWorkflow)

    def test_create_workflow_mixed(self):
        """Test creating workflow with mixed servers"""
        mock_plex = Mock()
        mock_plex.server_type = "plex"
        mock_jellyfin = Mock()
        mock_jellyfin.server_type = "jellyfin"

        workflow = WorkflowFactory.create_workflow([mock_plex, mock_jellyfin])
        assert isinstance(workflow, MixedWorkflow)


class TestStrategyFactory:
    """Test StrategyFactory"""

    def test_create_strategy_no_servers(self):
        """Test creating strategy with no servers"""
        strategy = StrategyFactory.create_strategy([])
        assert isinstance(strategy, FormBasedStrategy)

    def test_create_strategy_jellyfin_only(self):
        """Test creating strategy with Jellyfin only"""
        mock_server = Mock()
        mock_server.server_type = "jellyfin"

        strategy = StrategyFactory.create_strategy([mock_server])
        assert isinstance(strategy, FormBasedStrategy)

    def test_create_strategy_plex_only(self):
        """Test creating strategy with Plex only"""
        mock_server = Mock()
        mock_server.server_type = "plex"

        strategy = StrategyFactory.create_strategy([mock_server])
        assert isinstance(strategy, PlexOAuthStrategy)

    def test_create_strategy_mixed(self):
        """Test creating strategy with mixed servers"""
        mock_plex = Mock()
        mock_plex.server_type = "plex"
        mock_jellyfin = Mock()
        mock_jellyfin.server_type = "jellyfin"

        strategy = StrategyFactory.create_strategy([mock_plex, mock_jellyfin])
        assert isinstance(strategy, HybridStrategy)


class TestFormBasedStrategy:
    """Test FormBasedStrategy"""

    def test_authenticate_success(self):
        """Test successful authentication"""
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
        """Test authentication with missing field"""
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
        """Test authentication with password mismatch"""
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
        """Test getting required fields"""
        strategy = FormBasedStrategy()
        fields = strategy.get_required_fields()

        assert "username" in fields
        assert "email" in fields
        assert "password" in fields
        assert "confirm_password" in fields


class TestPlexOAuthStrategy:
    """Test PlexOAuthStrategy"""

    def test_authenticate_with_token(self):
        """Test authentication with OAuth token"""
        strategy = PlexOAuthStrategy()
        form_data = {"oauth_token": "test_token_123"}

        success, message, user_data = strategy.authenticate([], form_data)

        assert success is True
        assert message == "Plex OAuth authentication successful"
        assert user_data["plex_token"] == "test_token_123"

    def test_authenticate_missing_token(self, app):
        """Test authentication without token"""
        strategy = PlexOAuthStrategy()
        form_data = {}

        with app.test_request_context():
            success, message, user_data = strategy.authenticate([], form_data)

            assert success is False
            assert "OAuth token required" in message

    def test_get_required_fields(self):
        """Test getting required fields"""
        strategy = PlexOAuthStrategy()
        fields = strategy.get_required_fields()

        assert fields == []  # OAuth doesn't need form fields


class TestServerIntegrationRegistry:
    """Test ServerIntegrationRegistry"""

    def test_get_account_manager_jellyfin(self):
        """Test getting account manager for Jellyfin"""
        mock_server = Mock()
        mock_server.server_type = "jellyfin"

        manager = ServerIntegrationRegistry.get_account_manager(mock_server)
        assert isinstance(manager, FormBasedAccountManager)

    def test_get_account_manager_plex(self):
        """Test getting account manager for Plex"""
        mock_server = Mock()
        mock_server.server_type = "plex"

        manager = ServerIntegrationRegistry.get_account_manager(mock_server)
        assert isinstance(manager, PlexAccountManager)

    def test_get_account_manager_unknown(self):
        """Test getting account manager for unknown server"""
        mock_server = Mock()
        mock_server.server_type = "unknown"

        manager = ServerIntegrationRegistry.get_account_manager(mock_server)
        assert isinstance(manager, FormBasedAccountManager)  # Default fallback

    def test_get_supported_server_types(self):
        """Test getting supported server types"""
        supported = ServerIntegrationRegistry.get_supported_server_types()

        assert "plex" in supported
        assert "jellyfin" in supported
        assert "emby" in supported
        assert "audiobookshelf" in supported

    def test_register_server_type(self):
        """Test registering new server type"""

        class NewAccountManager(FormBasedAccountManager):
            pass

        ServerIntegrationRegistry.register_server_type("new_server", NewAccountManager)

        mock_server = Mock()
        mock_server.server_type = "new_server"

        manager = ServerIntegrationRegistry.get_account_manager(mock_server)
        assert isinstance(manager, NewAccountManager)


class TestFormBasedWorkflow:
    """Test FormBasedWorkflow"""

    def test_show_initial_form(self, app):
        """Test showing initial form"""
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
        """Test successful submission processing"""
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

        # Mock server processing
        with patch.object(workflow, "_process_servers") as mock_process:
            mock_server_result = Mock()
            mock_server_result.server.name = "Test Server"
            mock_server_result.message = "Success"
            mock_process.return_value = ([mock_server_result], [])

            with app.test_request_context():
                result = workflow.process_submission(mock_invitation, [], {})

                assert result.status == ProcessingStatus.SUCCESS
                assert result.redirect_url == "/wizard/"


class TestIntegrationWithDatabase:
    """Test integration with actual database"""

    def test_create_invitation_and_server(self, app):
        """Test creating invitation and server in database"""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            db.session.add(server)

            # Create invitation
            invitation = Invitation(code="DBTEST123", used=False, unlimited=False)
            db.session.add(invitation)

            db.session.commit()

            # Link them
            invitation.server = server
            db.session.commit()

            # Test that they're linked
            assert invitation.server == server
            assert invitation.server.server_type == "jellyfin"

            # Cleanup
            db.session.delete(invitation)
            db.session.delete(server)
            db.session.commit()

    def test_manager_with_database(self, app):
        """Test manager with database integration"""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            db.session.add(server)

            # Create invitation
            invitation = Invitation(code="DBTEST456", used=False, unlimited=False)
            db.session.add(invitation)

            db.session.commit()

            # Link them using the many-to-many relationship
            invitation.servers.append(server)
            db.session.commit()

            # Test manager
            manager = InvitationFlowManager()
            servers = manager._get_invitation_servers(invitation)

            assert len(servers) == 1
            assert servers[0].server_type == "jellyfin"

            # Cleanup
            db.session.delete(invitation)
            db.session.delete(server)
            db.session.commit()


class TestEndToEndFlow:
    """Test complete end-to-end flows"""

    @patch("app.services.invitation_flow.manager.is_invite_valid")
    @patch("app.services.invitation_flow.workflows.get_client_for_media_server")
    def test_complete_jellyfin_flow(self, mock_get_client, mock_is_valid, app):
        """Test complete Jellyfin invitation flow"""
        mock_is_valid.return_value = (True, "Valid invitation")

        # Mock client
        mock_client = Mock()
        mock_client.join.return_value = (True, "User created successfully")
        mock_get_client.return_value = mock_client

        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://test.example.com",
                api_key="test_key",
            )
            db.session.add(server)

            # Create invitation
            invitation = Invitation(code="E2E123", used=False, unlimited=False)
            db.session.add(invitation)

            db.session.commit()

            # Link them using the many-to-many relationship
            invitation.servers.append(server)
            db.session.commit()

            # Test display
            manager = InvitationFlowManager()
            display_result = manager.process_invitation_display("E2E123")

            assert display_result.status == ProcessingStatus.AUTHENTICATION_REQUIRED
            assert display_result.template_data is not None
            assert (
                display_result.template_data["template_name"] == "welcome-jellyfin.html"
            )

            # Test submission
            form_data = {
                "code": "E2E123",
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123",
                "confirm_password": "testpass123",
            }

            with patch("flask.session", {}):
                submission_result = manager.process_invitation_submission(form_data)

                assert submission_result.status == ProcessingStatus.SUCCESS
                assert submission_result.redirect_url == "/wizard/"

            # Cleanup
            db.session.delete(invitation)
            db.session.delete(server)
            db.session.commit()

    @patch("app.services.invitation_flow.manager.is_invite_valid")
    def test_complete_plex_flow(self, mock_is_valid, app):
        """Test complete Plex invitation flow"""
        mock_is_valid.return_value = (True, "Valid invitation")

        with app.app_context():
            # Create server
            server = MediaServer(
                name="Test Plex Server",
                server_type="plex",
                url="http://plex.example.com",
                api_key="test_key",
            )
            db.session.add(server)

            # Create invitation
            invitation = Invitation(code="PLEX123", used=False, unlimited=False)
            db.session.add(invitation)

            db.session.commit()

            # Link them using the many-to-many relationship
            invitation.servers.append(server)
            db.session.commit()

            # Test display
            manager = InvitationFlowManager()
            display_result = manager.process_invitation_display("PLEX123")

            assert display_result.status == ProcessingStatus.OAUTH_PENDING
            assert display_result.template_data is not None
            assert (
                display_result.template_data["template_name"] == "user-plex-login.html"
            )

            # Cleanup
            db.session.delete(invitation)
            db.session.delete(server)
            db.session.commit()
