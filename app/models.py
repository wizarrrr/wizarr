from datetime import UTC, datetime

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
    db.Column("server_id", db.Integer, db.ForeignKey("media_server.id"), nullable=True),
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
    used_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
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
    server_id = db.Column(db.Integer, db.ForeignKey("media_server.id"), nullable=True)
    server = db.relationship(
        "MediaServer", backref=db.backref("primary_invites", lazy=True)
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
    server_id = db.Column(db.Integer, db.ForeignKey("media_server.id"), nullable=True)
    server = db.relationship("MediaServer", backref=db.backref("users", lazy=True))
    identity_id = db.Column(db.Integer, db.ForeignKey("identity.id"), nullable=True)
    identity = db.relationship("Identity", backref=db.backref("accounts", lazy=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


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
        "MediaServer", backref=db.backref("connections", lazy=True)
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Library(db.Model):
    __tablename__ = "library"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String, nullable=False)  # e.g. Plex folder ID
    name = db.Column(db.String, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey("media_server.id"), nullable=True)
    server = db.relationship("MediaServer", backref=db.backref("libraries", lazy=True))

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
    an integer *position* starting at 0.  A `(server_type, position)` unique
    constraint guarantees a stable order without gaps.
    """

    __tablename__ = "wizard_step"

    id = db.Column(db.Integer, primary_key=True)

    # Target backend this step is meant for (plex / emby / etc.)
    server_type = db.Column(db.String, nullable=False)

    # Sort index within the server group – lower numbers appear first
    position = db.Column(db.Integer, nullable=False)

    # Optional page title – if omitted we will derive it from the first H1 in
    # the markdown when serving the wizard.
    title = db.Column(db.String, nullable=True)

    # Markdown source (front-end will render client-side preview)
    markdown = db.Column(db.Text, nullable=False)

    # List of setting keys that must evaluate to truthy for the step to show.
    # Mirrors the existing `requires:` front-matter array in the legacy files.
    requires = db.Column(db.JSON, nullable=True)

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
        db.UniqueConstraint("server_type", "position", name="uq_step_server_pos"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ── convenience helpers ─────────────────────────────────────────────
    def to_dict(self):
        """Return serialisable representation (for JSON responses)."""
        return {
            "id": self.id,
            "server_type": self.server_type,
            "position": self.position,
            "title": self.title,
            "markdown": self.markdown,
            "requires": self.requires or [],
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


class ExpiredUser(db.Model):
    """Track users that have been deleted due to expiry for monitoring and restoration."""

    __tablename__ = "expired_user"

    id = db.Column(db.Integer, primary_key=True)
    original_user_id = db.Column(db.Integer, nullable=False)  # Original User.id
    username = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    invitation_code = db.Column(db.String, nullable=True)
    server_id = db.Column(db.Integer, db.ForeignKey("media_server.id"), nullable=True)
    server = db.relationship(
        "MediaServer", backref=db.backref("expired_users", lazy=True)
    )
    expired_at = db.Column(
        db.DateTime, nullable=False
    )  # When user was supposed to expire
    deleted_at = db.Column(
        db.DateTime, default=lambda: datetime.now(UTC), nullable=False
    )  # When user was actually deleted

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
