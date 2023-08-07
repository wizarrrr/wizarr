from logging import error

from app.models.database.accounts import Accounts
from app.models.database.api_keys import APIKeys
from app.models.database.base import db
from app.models.database.invitations import Invitations
from app.models.database.libraries import Libraries
from app.models.database.notifications import Notifications
from app.models.database.sessions import Sessions
from app.models.database.settings import Settings
from app.models.database.users import Users
from app.models.database.oauth_clients import OAuthClients
from app.models.database.mfa import MFA

all_models = [Accounts, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions, OAuthClients, MFA]

try:
    db.create_tables(all_models, safe=True)
except Exception as e:
    error(f"Failed to create tables: {e}")
