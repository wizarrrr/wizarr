from datetime import datetime, timezone
from .extensions import db
from flask_login import UserMixin

invite_libraries = db.Table(
    "invite_library",
    db.Column("invite_id", db.Integer, db.ForeignKey("invitation.id"), primary_key=True),
    db.Column("library_id", db.Integer, db.ForeignKey("library.id"), primary_key=True),
)


class Invitation(db.Model):
    __tablename__ = 'invitation'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    used_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    used_by = db.relationship('User', backref=db.backref('invitations', lazy=True))
    expires = db.Column(db.DateTime, nullable=True)
    unlimited = db.Column(db.Boolean, nullable=True)
    duration = db.Column(db.String, nullable=True)
    specific_libraries = db.Column(db.String, nullable=True)
    plex_allow_sync = db.Column(db.Boolean, default=False, nullable=True)
    plex_home = db.Column(db.Boolean, default=False, nullable=True)
    plex_allow_channels = db.Column(db.Boolean, default=False, nullable=True)
    server_id = db.Column(db.Integer, db.ForeignKey('media_server.id'), nullable=True)
    server = db.relationship('MediaServer', backref=db.backref('invites', lazy=True))

    libraries = db.relationship(
        "Library",
        secondary=invite_libraries,
        back_populates="invites",
    )


class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, unique=True, nullable=False)
    value = db.Column(db.String, nullable=True)


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    code = db.Column(db.String, nullable=False)
    photo = db.Column(db.String, nullable=True)
    expires = db.Column(db.DateTime, nullable=True)
    password = db.Column(db.String, nullable=True)
    server_id = db.Column(db.Integer, db.ForeignKey('media_server.id'), nullable=True)
    server = db.relationship('MediaServer', backref=db.backref('users', lazy=True))
    identity_id = db.Column(db.Integer, db.ForeignKey('identity.id'), nullable=True)
    identity = db.relationship('Identity', backref=db.backref('accounts', lazy=True))


class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=True)
    password = db.Column(db.String, nullable=True)


class AdminUser(UserMixin):
    id = "admin"

    @property
    def username(self):
        return Settings.query.filter_by(key="admin_username").first().value


class MediaServer(db.Model):
    __tablename__ = 'media_server'

    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String, nullable=False)
    server_type = db.Column(db.String, nullable=False)  # plex, jellyfin, emby, etc.
    url = db.Column(db.String, nullable=False)
    api_key = db.Column(db.String, nullable=True)
    external_url = db.Column(db.String, nullable=True)  # Optional public address

    # Plex‐specific toggles (ignored by other server types)
    allow_downloads_plex = db.Column(db.Boolean, default=False, nullable=False)
    allow_tv_plex = db.Column(db.Boolean, default=False, nullable=False)

    # Whether the connection credentials were validated successfully
    verified = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Library(db.Model):
    __tablename__ = "library"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String, nullable=False)  # e.g. Plex folder ID
    name = db.Column(db.String, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('media_server.id'), nullable=True)
    server = db.relationship('MediaServer', backref=db.backref('libraries', lazy=True))

    # backref gives Invitation.libraries automatically
    invites = db.relationship(
        "Invitation",
        secondary=invite_libraries,
        back_populates="libraries",
    )

    __table_args__ = (
        db.UniqueConstraint("external_id", "server_id", name="uq_library_external_server"),
    )


class Identity(db.Model):
    __tablename__ = 'identity'
    id = db.Column(db.Integer, primary_key=True)
    primary_email = db.Column(db.String, nullable=True)
    primary_username = db.Column(db.String, nullable=True)
    nickname = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


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

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint("server_type", "position", name="uq_step_server_pos"),
    )

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
