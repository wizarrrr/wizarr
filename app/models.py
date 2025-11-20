import json
from datetime import UTC, datetime
from typing import Any

from flask_login import UserMixin

from .extensions import db

invite_libraries = db.Table(
    "invite_library",
    db.Column(
        "invite_id",
        db.Integer,
        db.ForeignKey("invitation.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "library_id",
        db.Integer,
        db.ForeignKey("library.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# New association table to enable multi-server invitations  (2025-06)
invitation_servers = db.Table(
    "invitation_server",
    db.Column(
        "invite_id",
        db.Integer,
        db.ForeignKey("invitation.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "server_id",
        db.Integer,
        db.ForeignKey("media_server.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # Track per-server usage so a single invite can be consumed independently
    db.Column("used", db.Boolean, default=False, nullable=False),
    db.Column("used_at", db.DateTime, nullable=True),
    # Track per-server expiry (overrides invitation.expires for this specific server)
    db.Column("expires", db.DateTime, nullable=True),
)

# ────────────────────────────────────────────────────────────────────────────
# New association table for tracking invitation usage by users (2025-08)
# ────────────────────────────────────────────────────────────────────────────
invitation_users = db.Table(
    "invitation_user",
    db.Column(
        "invite_id",
        db.Integer,
        db.ForeignKey("invitation.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # Track when this user used this invitation
    db.Column(
        "used_at", db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    ),
    # Track which server the user was created on when using this invitation
    db.Column(
        "server_id",
        db.Integer,
        db.ForeignKey("media_server.id", ondelete="SET NULL"),
        nullable=True,
    ),
)


class Invitation(db.Model):
    __tablename__ = "invitation"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # DEPRECATED: Legacy single-user relationship for backward compatibility
    # Will be removed in a future version - use 'users' relationship instead
    used_by_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    used_by = db.relationship("User", foreign_keys=[used_by_id])

    # NEW: Many-to-many relationship to track all users who used this invitation
    users = db.relationship(
        "User",
        secondary=invitation_users,
        backref=db.backref("used_invitations", lazy=True),
        lazy="select",
    )
    expires = db.Column(db.DateTime, nullable=True)
    unlimited = db.Column(db.Boolean, nullable=True)
    duration = db.Column(db.String, nullable=True)
    specific_libraries = db.Column(db.String, nullable=True)
    plex_allow_sync = db.Column(db.Boolean, default=False, nullable=True)
    plex_home = db.Column(db.Boolean, default=False, nullable=True)
    plex_allow_channels = db.Column(db.Boolean, default=False, nullable=True)
    server_id = db.Column(
        db.Integer, db.ForeignKey("media_server.id", ondelete="SET NULL"), nullable=True
    )
    server = db.relationship(
        "MediaServer",
        backref=db.backref("primary_invites", lazy=True, passive_deletes=True),
        passive_deletes=True,
    )

    libraries = db.relationship(
        "Library",
        secondary=invite_libraries,
        back_populates="invites",
    )

    # Link to one or many MediaServer rows (multi-server invites)
    servers = db.relationship(
        "MediaServer",
        secondary=invitation_servers,
        back_populates="invites",
    )

    # ── NEW: link invitation to an explicit wizard bundle ────────────
    wizard_bundle_id = db.Column(
        db.Integer, db.ForeignKey("wizard_bundle.id"), nullable=True
    )
    wizard_bundle = db.relationship(
        "WizardBundle", backref=db.backref("invitations", lazy=True)
    )

    # Universal invite toggles (work for all server types)
    allow_downloads = db.Column(db.Boolean, default=False, nullable=True)
    allow_live_tv = db.Column(db.Boolean, default=False, nullable=True)
    allow_mobile_uploads = db.Column(db.Boolean, default=False, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # Helper methods for the new many-to-many relationship
    def get_all_users(self):
        """Get all users who have used this invitation."""
        return list(self.users)

    def get_user_count(self):
        """Get the total number of users who have used this invitation."""
        return len(list(self.users))

    def get_first_user(self):
        """Get the first user who used this invitation (for backward compatibility)."""
        users_list = list(self.users)
        return users_list[0] if users_list else None

    def has_user(self, user):
        """Check if a specific user has used this invitation."""
        return user in list(self.users)


class Settings(db.Model):
    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, unique=True, nullable=False)
    value = db.Column(db.String, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    code = db.Column(db.String, nullable=False)
    photo = db.Column(db.String, nullable=True)
    expires = db.Column(db.DateTime, nullable=True)
    server_id = db.Column(
        db.Integer, db.ForeignKey("media_server.id", ondelete="CASCADE"), nullable=True
    )
    server = db.relationship(
        "MediaServer",
        backref=db.backref("users", lazy=True, passive_deletes=True),
        passive_deletes=True,
    )
    identity_id = db.Column(db.Integer, db.ForeignKey("identity.id"), nullable=True)
    identity = db.relationship("Identity", backref=db.backref("accounts", lazy=True))
    notes = db.Column(db.Text, nullable=True)
    is_disabled = db.Column(db.Boolean, nullable=False, default=False)

    # Standardized metadata columns
    is_admin = db.Column(db.Boolean, nullable=True, default=False)
    allow_downloads = db.Column(db.Boolean, nullable=True, default=False)
    allow_live_tv = db.Column(db.Boolean, nullable=True, default=False)
    allow_camera_upload = db.Column(db.Boolean, nullable=True, default=False)
    accessible_libraries = db.Column(
        db.Text, nullable=True
    )  # JSON array of library names

    # Legacy metadata caching fields (will be phased out)
    library_access_json = db.Column(db.Text, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_library_access(self):
        """Get deserialized library access data."""
        import json

        if not self.library_access_json:
            return None
        try:
            return json.loads(self.library_access_json)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_library_access(self, library_access):
        """Set library access data, serializing to JSON."""
        import json

        if library_access is None:
            self.library_access_json = None
        else:
            # Convert UserLibraryAccess objects to dicts if needed
            if (
                isinstance(library_access, list)
                and library_access
                and hasattr(library_access[0], "__dict__")
            ):
                # Convert dataclass objects to dicts
                library_access = [
                    {
                        "library_id": lib.library_id,
                        "library_name": lib.library_name,
                        "has_access": lib.has_access,
                    }
                    for lib in library_access
                ]
            self.library_access_json = json.dumps(library_access)

    def has_cached_metadata(self):
        """Check if user has cached metadata available."""
        return self.library_access_json is not None

    def get_accessible_libraries(self):
        """Get list of accessible library names."""
        import json

        if not self.accessible_libraries:
            return []
        try:
            return json.loads(self.accessible_libraries)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_accessible_libraries(self, libraries: list[str] | None):
        """Set list of accessible library names. None means full access."""
        import json

        if libraries is None or not libraries:
            self.accessible_libraries = None
        else:
            self.accessible_libraries = json.dumps(libraries)

    def update_standardized_metadata(self, details):
        """Update user with standardized metadata from MediaUserDetails."""
        from app.services.media.user_details import MediaUserDetails

        if not isinstance(details, MediaUserDetails):
            return

        skip_library_update = getattr(details, "library_access_unknown", False)

        # Update standardized columns
        self.is_admin = details.is_admin
        self.allow_downloads = getattr(details, "allow_downloads", False)
        self.allow_live_tv = getattr(details, "allow_live_tv", False)
        self.allow_camera_upload = getattr(details, "allow_camera_upload", False)

        if skip_library_update:
            return

        # Extract library names
        if details.library_access is None:
            # Full access - represent as None to display "All libraries"
            self.set_accessible_libraries(None)
        else:
            # Specific library access
            accessible_names = [
                lib.library_name for lib in details.library_access if lib.has_access
            ]
            self.set_accessible_libraries(accessible_names)


# ───────────────────────────────────────────────────────────────────────────────
#  Multi-admin support (2025-07)
# ───────────────────────────────────────────────────────────────────────────────
class AdminAccount(db.Model, UserMixin):
    """Dedicated model for administrator accounts.

    Replaces the legacy single-admin credentials that were stored as plain
    settings rows (``admin_username`` / ``admin_password``).  Each admin has a
    unique *username* and a hashed *password* (scrypt).  Because we inherit
    :class:`flask_login.UserMixin`, instances can be returned directly from
    ``login_user`` / ``user_loader``.
    """

    __tablename__ = "admin_account"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # ── helpers ────────────────────────────────────────────────────────────
    def set_password(self, raw_password: str):
        """Hash *raw_password* with *scrypt* and store it."""
        from werkzeug.security import (
            generate_password_hash,  # local import to avoid circular
        )

        self.password_hash = generate_password_hash(raw_password, "scrypt")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def check_password(self, raw_password: str) -> bool:
        """Validate *raw_password* against the stored *password_hash*."""
        from werkzeug.security import (
            check_password_hash,  # local import to avoid circular
        )

        return check_password_hash(self.password_hash, raw_password)


class Notification(db.Model):
    __tablename__ = "notification"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=True)
    password = db.Column(db.String, nullable=True)
    channel_id = db.Column(db.Integer, nullable=True)
    notification_events = db.Column(
        db.String, nullable=False, default="user_joined,update_available"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Connection(db.Model):
    """Server-to-server mapping for external integrations.

    Allows mapping specific media servers to specific external services,
    enabling per-server automation: invite from Server X → invite to Service X.
    Supports multiple connection types with varying requirements.
    """

    __tablename__ = "ombi_connection"
    id = db.Column(db.Integer, primary_key=True)
    connection_type = db.Column(
        db.String, nullable=False, default="ombi"
    )  # 'ombi' or 'overseerr'
    name = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=True)  # Optional for info-only connections
    api_key = db.Column(db.String, nullable=True)  # Optional for info-only connections
    media_server_id = db.Column(
        db.Integer, db.ForeignKey("media_server.id", ondelete="CASCADE"), nullable=False
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    media_server = db.relationship(
        "MediaServer",
        backref=db.backref("connections", lazy=True, passive_deletes=True),
        passive_deletes=True,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class AdminUser(UserMixin):
    id = "admin"

    @property
    def username(self):
        setting = Settings.query.filter_by(key="admin_username").first()
        return setting.value if setting else None


class MediaServer(db.Model):
    __tablename__ = "media_server"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    server_type = db.Column(db.String, nullable=False)  # plex, jellyfin, emby, etc.
    url = db.Column(db.String, nullable=False)
    api_key = db.Column(db.String, nullable=True)
    external_url = db.Column(db.String, nullable=True)  # Optional public address

    # Universal media server toggles (work for all server types)
    allow_downloads = db.Column(db.Boolean, default=False, nullable=False)
    allow_live_tv = db.Column(db.Boolean, default=False, nullable=False)
    allow_mobile_uploads = db.Column(db.Boolean, default=False, nullable=False)

    # Whether the connection credentials were validated successfully
    verified = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    # Reverse relationship for multi-server invites
    invites = db.relationship(
        "Invitation",
        secondary=invitation_servers,
        back_populates="servers",
    )
    historical_import_jobs = db.relationship(
        "HistoricalImportJob",
        back_populates="server",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Library(db.Model):
    __tablename__ = "library"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String, nullable=False)  # e.g. Plex folder ID
    name = db.Column(db.String, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    server_id = db.Column(
        db.Integer, db.ForeignKey("media_server.id", ondelete="CASCADE"), nullable=True
    )
    server = db.relationship(
        "MediaServer",
        backref=db.backref("libraries", lazy=True, passive_deletes=True),
        passive_deletes=True,
    )

    # backref gives Invitation.libraries automatically
    invites = db.relationship(
        "Invitation",
        secondary=invite_libraries,
        back_populates="libraries",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "external_id", "server_id", name="uq_library_external_server"
        ),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Identity(db.Model):
    __tablename__ = "identity"
    id = db.Column(db.Integer, primary_key=True)
    primary_email = db.Column(db.String, nullable=True)
    primary_username = db.Column(db.String, nullable=True)
    nickname = db.Column(db.String, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class WizardStep(db.Model):
    """Markdown wizard page stored in the database instead of loose files.

    Each *server_type* (plex, jellyfin, …) owns an ordered list of steps with
    an integer *position* starting at 0.  A `(server_type, category, position)` unique
    constraint guarantees a stable order without gaps within each category.

    The *category* field distinguishes between 'pre_invite' (shown before invitation
    acceptance) and 'post_invite' (shown after invitation acceptance) steps.
    """

    __tablename__ = "wizard_step"

    id = db.Column(db.Integer, primary_key=True)

    # Target backend this step is meant for (plex / emby / etc.)
    server_type = db.Column(db.String, nullable=False)

    # Category: 'pre_invite' or 'post_invite' - determines when step is shown
    category = db.Column(
        db.String,
        nullable=False,
        default="post_invite",
        server_default="post_invite",
    )

    # Sort index within the server group and category – lower numbers appear first
    position = db.Column(db.Integer, nullable=False)

    # Optional page title – if omitted we will derive it from the first H1 in
    # the markdown when serving the wizard.
    title = db.Column(db.String, nullable=True)

    # Markdown source (front-end will render client-side preview)
    markdown = db.Column(db.Text, nullable=False)

    # List of setting keys that must evaluate to truthy for the step to show.
    # Mirrors the existing `requires:` front-matter array in the legacy files.
    requires = db.Column(db.JSON, nullable=True)

    # New: require explicit user interaction before enabling Next
    require_interaction = db.Column(db.Boolean, default=False, nullable=True)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "server_type", "category", "position", name="uq_step_server_category_pos"
        ),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ── convenience helpers ─────────────────────────────────────────────
    def to_dict(self):
        """Return serialisable representation (for JSON responses)."""
        return {
            "id": self.id,
            "server_type": self.server_type,
            "category": self.category,
            "position": self.position,
            "title": self.title,
            "markdown": self.markdown,
            "requires": self.requires or [],
            "require_interaction": bool(self.require_interaction or False),
        }


# ───────────────────────────────────────────────────────────────────────────────
# New models powering custom "Wizard Bundles" (2025-07)
# ───────────────────────────────────────────────────────────────────────────────
class WizardBundle(db.Model):
    """A named collection of WizardStep pages shown in fixed order."""

    __tablename__ = "wizard_bundle"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)

    # Ordered list of steps belonging to this bundle
    steps = db.relationship(
        "WizardBundleStep",
        back_populates="bundle",
        cascade="all, delete-orphan",
        order_by="WizardBundleStep.position",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class WizardBundleStep(db.Model):
    """Mapping table assigning a WizardStep to a Bundle at a given position."""

    __tablename__ = "wizard_bundle_step"

    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(
        db.Integer,
        db.ForeignKey("wizard_bundle.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_id = db.Column(
        db.Integer, db.ForeignKey("wizard_step.id", ondelete="CASCADE"), nullable=False
    )
    position = db.Column(db.Integer, nullable=False)

    # Relationships
    bundle = db.relationship("WizardBundle", back_populates="steps")
    step = db.relationship("WizardStep")

    __table_args__ = (
        db.UniqueConstraint("bundle_id", "position", name="uq_bundle_pos"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class WebAuthnCredential(db.Model):
    """WebAuthn credential storage for passkey authentication."""

    __tablename__ = "webauthn_credential"

    id = db.Column(db.Integer, primary_key=True)
    admin_account_id = db.Column(
        db.Integer, db.ForeignKey("admin_account.id"), nullable=False
    )
    credential_id = db.Column(db.LargeBinary, nullable=False, unique=True)
    public_key = db.Column(db.LargeBinary, nullable=False)
    sign_count = db.Column(db.Integer, default=0, nullable=False)
    name = db.Column(db.String, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    last_used_at = db.Column(db.DateTime, nullable=True)

    admin_account = db.relationship(
        "AdminAccount",
        backref=db.backref(
            "webauthn_credentials", lazy=True, cascade="all, delete-orphan"
        ),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ApiKey(db.Model):
    """API keys for external access to Wizarr's API endpoints."""

    __tablename__ = "api_key"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)  # User-friendly name for the key
    key_hash = db.Column(db.String, nullable=False, unique=True)  # Hashed API key
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    last_used_at = db.Column(db.DateTime, nullable=True)
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("admin_account.id"), nullable=False
    )
    created_by = db.relationship(
        "AdminAccount", backref=db.backref("api_keys", lazy=True)
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class PasswordResetToken(db.Model):
    """Password reset tokens for media server users."""

    __tablename__ = "password_reset_token"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, nullable=False, unique=True)  # Reset token code
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user = db.relationship("User", backref=db.backref("reset_tokens", lazy=True))
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    expires_at = db.Column(db.DateTime, nullable=False)  # Token expiry (24 hours)
    used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def is_valid(self):
        """Check if token is still valid (not used and not expired)."""
        if self.used:
            return False
        now = datetime.now(UTC)
        expires_aware = self.expires_at.replace(tzinfo=UTC) if self.expires_at.tzinfo is None else self.expires_at
        return expires_aware > now


class ExpiredUser(db.Model):
    """Track users that have been deleted due to expiry for monitoring and restoration."""

    __tablename__ = "expired_user"

    id = db.Column(db.Integer, primary_key=True)
    original_user_id = db.Column(db.Integer, nullable=False)  # Original User.id
    username = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    invitation_code = db.Column(db.String, nullable=True)
    server_id = db.Column(
        db.Integer, db.ForeignKey("media_server.id", ondelete="CASCADE"), nullable=True
    )
    server = db.relationship(
        "MediaServer",
        backref=db.backref("expired_users", lazy=True, passive_deletes=True),
        passive_deletes=True,
    )
    expired_at = db.Column(
        db.DateTime, nullable=False
    )  # When user was supposed to expire
    deleted_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )  # When user was actually deleted

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ActivitySession(db.Model):
    __tablename__ = "activity_session"

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(
        db.Integer, db.ForeignKey("media_server.id", ondelete="CASCADE"), nullable=False
    )
    session_id = db.Column(db.String, nullable=False, index=True)
    reference_id = db.Column(db.Integer, nullable=True, index=True)
    user_name = db.Column(db.String, nullable=False, index=True)
    user_id = db.Column(db.String, nullable=True)
    media_title = db.Column(db.String, nullable=False)
    media_type = db.Column(db.String, nullable=True, index=True)
    media_id = db.Column(db.String, nullable=True)
    series_name = db.Column(db.String, nullable=True)
    season_number = db.Column(db.Integer, nullable=True)
    episode_number = db.Column(db.Integer, nullable=True)
    started_at = db.Column(
        db.DateTime, nullable=False, index=True, default=lambda: datetime.now(UTC)
    )
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    duration_ms = db.Column(db.BigInteger, nullable=True)
    device_name = db.Column(db.String, nullable=True)
    client_name = db.Column(db.String, nullable=True)
    ip_address = db.Column(db.String, nullable=True)
    platform = db.Column(db.String, nullable=True)
    player_version = db.Column(db.String, nullable=True)
    transcoding_info = db.Column(db.Text, nullable=True)
    session_metadata = db.Column(db.Text, nullable=True)
    artwork_url = db.Column(db.String, nullable=True)
    thumbnail_url = db.Column(db.String, nullable=True)
    wizarr_user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    wizarr_identity_id = db.Column(
        db.Integer, db.ForeignKey("identity.id"), nullable=True, index=True
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    server = db.relationship(
        "MediaServer",
        backref=db.backref("activity_sessions", lazy=True, passive_deletes=True),
        passive_deletes=True,
    )
    snapshots = db.relationship(
        "ActivitySnapshot",
        backref=db.backref("session", passive_deletes=True),
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    wizarr_user = db.relationship("User", foreign_keys=[wizarr_user_id], lazy="joined")
    wizarr_identity = db.relationship(
        "Identity", foreign_keys=[wizarr_identity_id], lazy="joined"
    )

    __table_args__ = (
        db.Index("ix_activity_session_server_started", "server_id", "started_at"),
        db.Index("ix_activity_session_user_started", "user_name", "started_at"),
    )

    def get_transcoding_info(self) -> dict[str, Any]:
        if not self.transcoding_info:
            return {}
        try:
            return json.loads(self.transcoding_info)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_transcoding_info(self, info: dict[str, Any]):
        if info is None:
            self.transcoding_info = None
        else:
            self.transcoding_info = json.dumps(info, default=str)

    def get_metadata(self) -> dict[str, Any]:
        if not self.session_metadata:
            return {}
        try:
            return json.loads(self.session_metadata)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_metadata(self, metadata: dict[str, Any]):
        if metadata is None:
            self.session_metadata = None
        else:
            self.session_metadata = json.dumps(metadata, default=str)

    @property
    def duration_minutes(self) -> float | None:
        if self.duration_ms is None:
            return None
        return self.duration_ms / (1000 * 60)

    @property
    def is_active(self) -> bool:
        return bool(self.active)

    @property
    def display_duration_seconds(self) -> int | None:
        if self.duration_ms:
            return max(int(self.duration_ms // 1000), 0)
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "server_id": self.server_id,
            "session_id": self.session_id,
            "user_name": self.user_name,
            "user_id": self.user_id,
            "media_title": self.media_title,
            "media_type": self.media_type,
            "media_id": self.media_id,
            "series_name": self.series_name,
            "season_number": self.season_number,
            "episode_number": self.episode_number,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "duration_ms": self.duration_ms,
            "device_name": self.device_name,
            "client_name": self.client_name,
            "ip_address": self.ip_address,
            "platform": self.platform,
            "player_version": self.player_version,
            "transcoding_info": self.get_transcoding_info(),
            "metadata": self.get_metadata(),
            "artwork_url": self.artwork_url,
            "thumbnail_url": self.thumbnail_url,
            "duration_minutes": self.duration_minutes,
            "display_duration_seconds": self.display_duration_seconds,
            "is_active": self.is_active,
            "active": bool(self.active),
            "wizarr_user_id": self.wizarr_user_id,
            "wizarr_identity_id": self.wizarr_identity_id,
            "display_user_name": self.display_user_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def display_user_name(self) -> str:
        if hasattr(self, "_resolved_identity_name") and self._resolved_identity_name:
            return self._resolved_identity_name

        identity = None
        if self.wizarr_identity:
            identity = self.wizarr_identity
        elif getattr(self, "wizarr_user", None) and getattr(
            self.wizarr_user, "identity", None
        ):
            identity = self.wizarr_user.identity

        if identity:
            return identity.nickname or identity.primary_username or self.user_name

        return self.user_name

    def is_valid_for_statistics(self) -> bool:
        """
        Check if session has complete data for statistics (Tautulli-inspired).

        Returns False if critical fields contain "Unknown" values, allowing
        queries to filter out incomplete sessions from statistics and dashboards.

        This follows Tautulli's approach of dual persistence: all sessions are
        captured immediately, but only validated sessions are used for analytics.

        Note: device_name can be NULL for historical imports, so we allow NULL
        but exclude "Unknown" string values.
        """
        # Check if critical fields are Unknown
        unknown_values = {"unknown", "unknown user", "unknown device"}

        if not self.user_name or self.user_name.lower() in unknown_values:
            return False

        if not self.media_title or self.media_title.lower() in unknown_values:
            return False

        # Device name can be NULL for historical imports
        if self.device_name:
            return self.device_name.lower() not in unknown_values
        return True


class HistoricalImportJob(db.Model):
    __tablename__ = "historical_import_job"

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(
        db.Integer,
        db.ForeignKey("media_server.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    days_back = db.Column(db.Integer, nullable=False)
    max_results = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="queued", index=True)
    total_fetched = db.Column(db.Integer, nullable=False, default=0)
    total_processed = db.Column(db.Integer, nullable=False, default=0)
    total_stored = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    server = db.relationship(
        "MediaServer",
        back_populates="historical_import_jobs",
        lazy="joined",
        passive_deletes=True,
    )

    __table_args__ = (
        db.Index("ix_historical_import_job_server_status", "server_id", "status"),
    )

    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def progress_percent(self) -> int:
        if self.total_fetched and self.total_fetched > 0:
            return max(
                0,
                min(
                    100,
                    int((self.total_processed / max(self.total_fetched, 1)) * 100),
                ),
            )
        return 0

    @property
    def is_active(self) -> bool:
        return self.status in {self.STATUS_RUNNING, self.STATUS_QUEUED}

    @property
    def status_label(self) -> str:
        return self.status.replace("_", " ").title()


class ActivitySnapshot(db.Model):
    __tablename__ = "activity_snapshot"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("activity_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp = db.Column(
        db.DateTime, nullable=False, index=True, default=lambda: datetime.now(UTC)
    )
    position_ms = db.Column(db.BigInteger, nullable=True)
    state = db.Column(db.String, nullable=False, index=True)
    transcoding_details = db.Column(db.Text, nullable=True)
    bandwidth_kbps = db.Column(db.Integer, nullable=True)
    quality = db.Column(db.String, nullable=True)
    subtitle_stream = db.Column(db.String, nullable=True)
    audio_stream = db.Column(db.String, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        db.Index("ix_activity_snapshot_session_timestamp", "session_id", "timestamp"),
    )

    def get_transcoding_details(self) -> dict[str, Any]:
        if not self.transcoding_details:
            return {}
        try:
            return json.loads(self.transcoding_details)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_transcoding_details(self, details: dict[str, Any]):
        if details is None:
            self.transcoding_details = None
        else:
            self.transcoding_details = json.dumps(details, default=str)

    @property
    def position_minutes(self) -> float | None:
        if self.position_ms is None:
            return None
        return self.position_ms / (1000 * 60)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "position_ms": self.position_ms,
            "state": self.state,
            "transcoding_details": self.get_transcoding_details(),
            "bandwidth_kbps": self.bandwidth_kbps,
            "quality": self.quality,
            "subtitle_stream": self.subtitle_stream,
            "audio_stream": self.audio_stream,
            "position_minutes": self.position_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
