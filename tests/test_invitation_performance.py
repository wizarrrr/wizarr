"""
Performance and load tests for invitation system.

These tests ensure the invitation system can handle concurrent users
and process invitations efficiently.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from statistics import mean, median
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import Invitation, MediaServer, User
from app.services.invitation_manager import InvitationManager
from tests.mocks.media_server_mocks import (
    create_mock_client,
    get_mock_state,
    setup_mock_servers,
)


class TestInvitationPerformance:
    """Test invitation processing performance."""

    def setup_method(self):
        """Setup for each test."""
        setup_mock_servers()

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_single_invitation_processing_time(self, mock_get_client, app):
        """Test time to process a single invitation."""
        with app.app_context():
            # Setup
            server = MediaServer(
                name="Performance Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="perf-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(code="PERF123", unlimited=True)
            invitation.servers = [server]
            db.session.add(invitation)
            db.session.commit()

            mock_client = create_mock_client("jellyfin", server_id=server.id)
            mock_get_client.return_value = mock_client

            # Measure processing time
            start_time = time.time()

            success, redirect_code, errors = InvitationManager.process_invitation(
                code="PERF123",
                username="perfuser",
                password="testpass123",
                confirm_password="testpass123",
                email="perf@example.com",
            )

            end_time = time.time()
            processing_time = end_time - start_time

            # Verify success
            assert success
            assert len(errors) == 0

            # Performance assertion - should complete in under 1 second
            assert processing_time < 1.0, (
                f"Processing took {processing_time:.3f}s, expected < 1.0s"
            )

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_concurrent_invitation_processing(self, mock_get_client, app):
        """Test processing multiple invitations concurrently."""
        with app.app_context():
            # Setup server and unlimited invitation
            server = MediaServer(
                name="Concurrent Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="concurrent-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(
                code="CONCURRENT123",
                unlimited=True,  # Allow multiple uses
            )
            invitation.servers = [server]
            db.session.add(invitation)
            db.session.commit()

            mock_client = create_mock_client("jellyfin", server_id=server.id)
            mock_get_client.return_value = mock_client

            # Function to process invitation
            def process_invitation(user_id):
                with app.app_context():
                    success, redirect_code, errors = (
                        InvitationManager.process_invitation(
                            code="CONCURRENT123",
                            username=f"user{user_id}",
                            password="testpass123",
                            confirm_password="testpass123",
                            email=f"user{user_id}@example.com",
                        )
                    )
                    return success, redirect_code, errors, user_id

            # Process 10 invitations concurrently
            num_users = 10
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(process_invitation, i) for i in range(num_users)
                ]
                results = [future.result() for future in futures]

            end_time = time.time()
            total_time = end_time - start_time

            # Verify all succeeded
            successful_count = sum(1 for success, _, _, _ in results if success)
            assert successful_count == num_users, (
                f"Only {successful_count}/{num_users} invitations succeeded"
            )

            # Performance assertion - should handle 10 concurrent users in reasonable time
            assert total_time < 5.0, (
                f"Concurrent processing took {total_time:.3f}s, expected < 5.0s"
            )

            # Verify users were created
            created_users = get_mock_state().users
            assert len(created_users) == num_users

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_multi_server_invitation_performance(self, mock_get_client, app):
        """Test performance of multi-server invitation processing."""
        with app.app_context():
            setup_mock_servers()

            # Create multiple servers
            servers = []
            for i in range(3):  # 3 servers
                server = MediaServer(
                    name=f"Server {i + 1}",
                    server_type="jellyfin",
                    url=f"http://localhost:809{6 + i}",
                    api_key=f"key{i + 1}",
                )
                servers.append(server)
                db.session.add(server)
            db.session.flush()

            # Create multi-server invitation
            invitation = Invitation(code="MULTIPERFORMANCE123", unlimited=False)
            invitation.servers = servers
            db.session.add(invitation)
            db.session.commit()

            # Setup mock clients
            def get_client_side_effect(server):
                return create_mock_client("jellyfin", server_id=server.id)

            mock_get_client.side_effect = get_client_side_effect

            # Measure processing time
            start_time = time.time()

            success, redirect_code, errors = InvitationManager.process_invitation(
                code="MULTIPERFORMANCE123",
                username="multiuser",
                password="testpass123",
                confirm_password="testpass123",
                email="multi@example.com",
            )

            end_time = time.time()
            processing_time = end_time - start_time

            # Verify success
            assert success
            assert len(errors) == 0

            # Should process 3 servers in reasonable time
            assert processing_time < 3.0, (
                f"Multi-server processing took {processing_time:.3f}s, expected < 3.0s"
            )

            # Verify users created on all servers
            created_users = get_mock_state().users
            assert len(created_users) == 3


class TestInvitationLoadTesting:
    """Load testing for invitation system."""

    def setup_method(self):
        """Setup for each test."""
        setup_mock_servers()

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_invitation_validation_performance(self, mock_get_client, app):
        """Test performance of invitation validation under load."""
        with app.app_context():
            # Create multiple invitations
            server = MediaServer(
                name="Load Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="load-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create 100 invitations
            invitations = []
            for i in range(100):
                invitation = Invitation(code=f"LOAD{i:03d}", unlimited=True)
                invitation.servers = [server]
                invitations.append(invitation)
                db.session.add(invitation)
            db.session.commit()

            # Test validation performance
            from app.services.invites import is_invite_valid

            validation_times = []

            for invitation in invitations[:20]:  # Test first 20
                start_time = time.time()
                is_valid, message = is_invite_valid(invitation.code)
                end_time = time.time()

                validation_times.append(end_time - start_time)
                assert is_valid  # Should all be valid

            # Performance analysis
            avg_time = mean(validation_times)
            median_time = median(validation_times)
            max_time = max(validation_times)

            # Assertions
            assert avg_time < 0.01, f"Average validation time {avg_time:.4f}s too slow"
            assert median_time < 0.01, (
                f"Median validation time {median_time:.4f}s too slow"
            )
            assert max_time < 0.05, f"Max validation time {max_time:.4f}s too slow"

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_database_performance_under_load(self, mock_get_client, app):
        """Test database performance with many invitation records."""
        with app.app_context():
            # Create server
            server = MediaServer(
                name="DB Load Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="db-load-key",
            )
            db.session.add(server)
            db.session.flush()

            # Create many invitations and users to simulate realistic load
            for i in range(500):  # 500 invitations
                invitation = Invitation(
                    code=f"DBLOAD{i:04d}",
                    unlimited=False,
                    used=(i % 3 == 0),  # Every 3rd invitation is used
                )
                invitation.servers = [server]
                db.session.add(invitation)

                if invitation.used:
                    # Create corresponding user
                    user = User(
                        username=f"user{i}",
                        email=f"user{i}@example.com",
                        token=f"token{i}",
                        code=invitation.code,
                        server_id=server.id,
                    )
                    db.session.add(user)

            db.session.commit()

            # Test query performance
            start_time = time.time()

            # Simulate typical queries during invitation processing
            for i in range(10):
                code = f"DBLOAD{i:04d}"
                invitation = Invitation.query.filter_by(code=code).first()
                assert invitation is not None

                # Check if user exists (typical validation)
                user = User.query.filter_by(code=code, server_id=server.id).first()

            end_time = time.time()
            query_time = end_time - start_time

            # Should handle queries efficiently even with large dataset
            assert query_time < 1.0, (
                f"Database queries took {query_time:.3f}s, expected < 1.0s"
            )


class TestInvitationMemoryUsage:
    """Test memory usage during invitation processing."""

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_memory_efficient_processing(self, mock_get_client, app):
        """Test that invitation processing doesn't leak memory."""
        import gc
        import tracemalloc

        with app.app_context():
            # Setup
            server = MediaServer(
                name="Memory Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="memory-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(code="MEMORY123", unlimited=True)
            invitation.servers = [server]
            db.session.add(invitation)
            db.session.commit()

            mock_client = create_mock_client("jellyfin", server_id=server.id)
            mock_get_client.return_value = mock_client

            # Start memory tracking
            tracemalloc.start()

            # Process multiple invitations
            for i in range(50):
                success, redirect_code, errors = InvitationManager.process_invitation(
                    code="MEMORY123",
                    username=f"memuser{i}",
                    password="testpass123",
                    confirm_password="testpass123",
                    email=f"memuser{i}@example.com",
                )
                assert success

                # Force garbage collection periodically
                if i % 10 == 0:
                    gc.collect()

            # Check memory usage
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Memory should be reasonable (less than 50MB peak)
            peak_mb = peak / 1024 / 1024
            assert peak_mb < 50, f"Peak memory usage {peak_mb:.2f}MB too high"


class TestInvitationErrorRecovery:
    """Test system recovery from errors during high load."""

    def setup_method(self):
        """Setup for each test."""
        setup_mock_servers()

    @patch("app.services.invitation_manager.get_client_for_media_server")
    def test_recovery_from_server_failures(self, mock_get_client, app):
        """Test system recovery when servers fail under load."""
        with app.app_context():
            # Setup server
            server = MediaServer(
                name="Failure Recovery Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="recovery-key",
            )
            db.session.add(server)
            db.session.flush()

            invitation = Invitation(code="RECOVERY123", unlimited=True)
            invitation.servers = [server]
            db.session.add(invitation)
            db.session.commit()

            # Setup client that fails intermittently
            success_count = 0
            failure_count = 0

            def intermittent_client(server):
                nonlocal success_count, failure_count
                client = create_mock_client("jellyfin", server_id=server.id)

                original_join = client._do_join

                def failing_join(*args, **kwargs):
                    nonlocal success_count, failure_count
                    # Fail every 3rd request
                    if (success_count + failure_count) % 3 == 2:
                        failure_count += 1
                        return False, "Temporary server error"
                    success_count += 1
                    return original_join(*args, **kwargs)

                client._do_join = failing_join
                return client

            mock_get_client.side_effect = intermittent_client

            # Process invitations - some should fail, others succeed
            results = []
            for i in range(20):
                success, redirect_code, errors = InvitationManager.process_invitation(
                    code="RECOVERY123",
                    username=f"recoveryuser{i}",
                    password="testpass123",
                    confirm_password="testpass123",
                    email=f"recovery{i}@example.com",
                )
                results.append(success)

            # Should have both successes and failures
            successful_count = sum(results)
            failed_count = len(results) - successful_count

            assert successful_count > 0, "No invitations succeeded"
            assert failed_count > 0, "No invitations failed (test setup issue)"

            # System should remain stable
            assert successful_count >= failed_count, (
                "More failures than successes indicates system instability"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to see print output
