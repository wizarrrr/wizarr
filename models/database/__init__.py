from logging import error

from models.database.accounts import Accounts
from models.database.api_keys import APIKeys
from models.database.base import db
from models.database.invitations import Invitations
from models.database.libraries import Libraries
from models.database.notifications import Notifications
from models.database.sessions import Sessions
from models.database.settings import Settings
from models.database.users import Users
from models.database.oauth_clients import OAuthClients
from models.database.mfa import MFA

all_models = [Accounts, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions, OAuthClients, MFA]

try:
    db.create_tables(all_models, safe=True)
except Exception as e:
    error(f"Failed to create tables: {e}")
