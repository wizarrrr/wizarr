# app/scripts/migrate_libraries.py

from app.extensions import db
from app.models import Invitation, Library, Settings


def update_server_verified(app):
    # Function to convert server_verified = "true" to server_verified = True
    with app.app_context():
        # 1) load the Settings row
        row = Settings.query.filter_by(key="server_verified").first()
        if not row or not row.value:
            # nothing to migrate
            return

        # 2) convert string to boolean
        if row.value == "1":
            row.value = "true"

        db.session.commit()


def run_library_migration(app):
    """Idempotently pull old comma-list out of Settings.libraries,
    turn them into Library rows & Invitation<>Library links,
    then delete that Settings entry so future runs skip it."""
    with app.app_context():
        # 1) load the Settings row
        row = Settings.query.filter_by(key="libraries").first()
        if not row or not row.value:
            # nothing to migrate
            return

        # 2) parse out all the ext-ids
        old_ext_ids = [s.strip() for s in row.value.split(",") if s.strip()]
        if not old_ext_ids:
            # empty list → just delete and quit
            db.session.delete(row)
            db.session.commit()
            return

        # 3) upsert each Library record associated with available servers
        # In multi-server Wizarr, we don't create orphaned global libraries
        from app.models import MediaServer

        servers = MediaServer.query.filter_by(verified=True).all()
        if not servers:
            # No verified servers available - skip creating libraries
            # This prevents orphaned libraries without server association
            pass
        else:
            # Create libraries for each verified server if they don't exist
            for server in servers:
                for ext in old_ext_ids:
                    lib = Library.query.filter_by(
                        external_id=ext, server_id=server.id
                    ).first()
                    if not lib:
                        db.session.add(
                            Library(
                                external_id=ext,
                                name=ext,
                                enabled=True,
                                server_id=server.id,
                            )
                        )

        # 4) remove that Settings row entirely so we never run again
        db.session.delete(row)

        db.session.commit()

        # 5) now wire up per-invite links
        # Link libraries to invitations based on their associated server(s)
        total_links = 0
        for inv in Invitation.query:
            if inv.specific_libraries:
                parts = [
                    s.strip() for s in inv.specific_libraries.split(",") if s.strip()
                ]

                # Get relevant servers for this invitation
                invitation_servers = []
                if inv.servers:  # Multi-server relationship
                    invitation_servers = inv.servers
                elif inv.server_id:  # Legacy single server
                    from app.models import MediaServer

                    server = MediaServer.query.get(inv.server_id)
                    if server:
                        invitation_servers = [server]

                # Link libraries from the invitation's servers
                for server in invitation_servers:
                    for ext in parts:
                        lib = Library.query.filter_by(
                            external_id=ext, server_id=server.id
                        ).first()
                        if lib and lib not in inv.libraries:
                            inv.libraries.append(lib)
                            total_links += 1

                # clear out the old CSV field
                inv.specific_libraries = None

        db.session.commit()
        # Migration completed silently - details logged by caller if needed
