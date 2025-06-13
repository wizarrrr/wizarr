from app.extensions import db
from app.models import Settings, MediaServer, Library, User, Invitation


def migrate_single_to_multi(app):
    """If no MediaServer rows exist but legacy Settings rows do, create one
    MediaServer and attach existing Library/User rows to it.

    This is idempotent: subsequent runs will do nothing once a MediaServer exists
    or if there is no legacy configuration to import.
    """
    with app.app_context():
        # Already migrated?
        if MediaServer.query.first() is not None:
            return

        # Check if an admin user exists
        admin_setting = Settings.query.filter_by(key="admin_username").first()
        if not admin_setting or not admin_setting.value:
            # No admin user yet, do not auto-create a MediaServer
            return

        # Gather legacy settings
        keys = [
            "server_name",
            "server_type",
            "server_url",
            "api_key",
            "allow_downloads_plex",
            "allow_tv_plex",
            "server_verified",
        ]
        rows = (
            Settings.query
            .filter(Settings.key.in_(keys))
            .all()
        )
        legacy = {r.key: r.value for r in rows}

        # Need at minimum a URL to create a server record
        if not legacy.get("server_url"):
            # Nothing to migrate (fresh install or wizard not completed)
            return

        def _to_bool(v: str | None) -> bool:
            return str(v).lower() in {"1", "true", "yes", "on"}

        server = MediaServer(
            name=legacy.get("server_name") or "Default",
            server_type=legacy.get("server_type") or "plex",
            url=legacy["server_url"],
            api_key=legacy.get("api_key"),
            allow_downloads_plex=_to_bool(legacy.get("allow_downloads_plex")),
            allow_tv_plex=_to_bool(legacy.get("allow_tv_plex")),
            verified=_to_bool(legacy.get("server_verified")),
        )
        db.session.add(server)
        db.session.flush()  # obtain server.id

        # Attach existing libraries & users & invitations
        Library.query.filter_by(server_id=None).update({"server_id": server.id})
        User.query.filter_by(server_id=None).update({"server_id": server.id})
        Invitation.query.filter_by(server_id=None).update({"server_id": server.id})
        db.session.commit()

        print(f"[migrate_media_server] Created initial MediaServer(id={server.id}) and linked existing data.") 