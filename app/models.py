from datetime import datetime
from .extensions import db
from flask_login import UserMixin

class Invitation(db.Model):
    __tablename__ = 'invitation'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    used_by = db.Column(db.String, nullable=True)
    expires = db.Column(db.DateTime, nullable=True)
    unlimited = db.Column(db.Boolean, nullable=True)
    duration = db.Column(db.String, nullable=True)
    specific_libraries = db.Column(db.String, nullable=True)
    plex_allow_sync = db.Column(db.Boolean, default=False, nullable=False)
    plex_home = db.Column(db.Boolean, default=False, nullable=False)

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
    email = db.Column(db.String, nullable=False)
    code = db.Column(db.String, nullable=False)
    photo = db.Column(db.String, nullable=True)
    expires = db.Column(db.DateTime, nullable=True)

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
        from .models import Settings
        return Settings.query.filter_by(key="admin_username").first().value
