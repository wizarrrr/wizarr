"""Test media server deletion with foreign key constraints."""

from app.models import (
    ActivitySession,
    ExpiredUser,
    HistoricalImportJob,
    Invitation,
    Library,
    MediaServer,
    User,
)


def test_delete_media_server_with_related_entities(session):
    """Test that deleting a media server also deletes all related entities."""
    # Create a media server
    server = MediaServer(
        name="Test Jellyfin Server",
        server_type="jellyfin",
        url="http://localhost:8096",
        api_key="test_api_key",
        verified=True,
    )
    session.add(server)
    session.commit()
    server_id = server.id

    # Create related entities
    
    # 1. Library
    library = Library(
        external_id="lib1",
        name="Movies",
        server_id=server_id,
        enabled=True,
    )
    session.add(library)

    # 2. User
    user = User(
        token="test_token",
        username="test_user",
        code="test_code",
        server_id=server_id,
    )
    session.add(user)

    # 3. ExpiredUser
    from datetime import UTC, datetime
    expired_user = ExpiredUser(
        original_user_id=123,
        username="expired_user",
        server_id=server_id,
        expired_at=datetime.now(UTC),
    )
    session.add(expired_user)

    # 4. ActivitySession
    activity = ActivitySession(
        server_id=server_id,
        session_id="session123",
        user_name="test_user",
        media_title="Test Movie",
    )
    session.add(activity)

    # 5. HistoricalImportJob
    import_job = HistoricalImportJob(
        server_id=server_id,
        days_back=30,
        status="completed",
    )
    session.add(import_job)

    # 6. Invitation with server_id reference
    invitation = Invitation(
        code="INVITE123",
        server_id=server_id,
    )
    session.add(invitation)

    session.commit()

    # Verify entities exist
    assert session.query(MediaServer).filter_by(id=server_id).first() is not None
    assert session.query(Library).filter_by(server_id=server_id).count() == 1
    assert session.query(User).filter_by(server_id=server_id).count() == 1
    assert session.query(ExpiredUser).filter_by(server_id=server_id).count() == 1
    assert session.query(ActivitySession).filter_by(server_id=server_id).count() == 1
    assert session.query(HistoricalImportJob).filter_by(server_id=server_id).count() == 1
    assert session.query(Invitation).filter_by(server_id=server_id).count() == 1

    # Now delete the media server following the same logic as delete_server()
    
    # 1) Delete libraries
    session.query(Library).filter(Library.server_id == server_id).delete(
        synchronize_session=False
    )
    
    # 2) Delete expired users
    session.query(ExpiredUser).filter(ExpiredUser.server_id == server_id).delete(
        synchronize_session=False
    )
    
    # 3) Delete activity sessions
    session.query(ActivitySession).filter(ActivitySession.server_id == server_id).delete(
        synchronize_session=False
    )
    
    # 4) Delete historical import jobs
    session.query(HistoricalImportJob).filter(HistoricalImportJob.server_id == server_id).delete(
        synchronize_session=False
    )
    
    # 5) Clean up invitation_users association table
    from sqlalchemy import text
    session.execute(
        text("DELETE FROM invitation_user WHERE server_id = :server_id"),
        {"server_id": server_id}
    )
    
    # 6) Set server_id to NULL for invitations
    session.query(Invitation).filter(Invitation.server_id == server_id).update(
        {"server_id": None}, synchronize_session=False
    )
    
    # 7) Delete users
    session.query(User).filter(User.server_id == server_id).delete(
        synchronize_session=False
    )
    
    # 8) Delete the media server
    session.query(MediaServer).filter_by(id=server_id).delete(synchronize_session=False)
    
    session.commit()

    # Verify entities are deleted
    assert session.query(MediaServer).filter_by(id=server_id).first() is None
    assert session.query(Library).filter_by(server_id=server_id).count() == 0
    assert session.query(User).filter_by(server_id=server_id).count() == 0
    assert session.query(ExpiredUser).filter_by(server_id=server_id).count() == 0
    assert session.query(ActivitySession).filter_by(server_id=server_id).count() == 0
    assert session.query(HistoricalImportJob).filter_by(server_id=server_id).count() == 0
    
    # Verify invitation still exists but with server_id set to NULL
    inv = session.query(Invitation).filter_by(code="INVITE123").first()
    assert inv is not None
    assert inv.server_id is None


def test_delete_media_server_without_related_entities(session):
    """Test that deleting a media server without related entities works."""
    # Create a media server without related entities
    server = MediaServer(
        name="Empty Server",
        server_type="plex",
        url="http://localhost:32400",
        api_key="empty_key",
        verified=True,
    )
    session.add(server)
    session.commit()
    server_id = server.id

    # Verify server exists
    assert session.query(MediaServer).filter_by(id=server_id).first() is not None

    # Delete the server (should work without errors even with no related entities)
    session.query(Library).filter(Library.server_id == server_id).delete(
        synchronize_session=False
    )
    session.query(ExpiredUser).filter(ExpiredUser.server_id == server_id).delete(
        synchronize_session=False
    )
    session.query(ActivitySession).filter(ActivitySession.server_id == server_id).delete(
        synchronize_session=False
    )
    session.query(HistoricalImportJob).filter(HistoricalImportJob.server_id == server_id).delete(
        synchronize_session=False
    )
    session.query(Invitation).filter(Invitation.server_id == server_id).update(
        {"server_id": None}, synchronize_session=False
    )
    session.query(User).filter(User.server_id == server_id).delete(
        synchronize_session=False
    )
    session.query(MediaServer).filter_by(id=server_id).delete(synchronize_session=False)
    session.commit()

    # Verify server is deleted
    assert session.query(MediaServer).filter_by(id=server_id).first() is None
