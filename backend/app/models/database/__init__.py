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
from app.models.database.discord import Discord
from app.models.database.webhooks import Webhooks
from app.models.database.requests import Requests
from app.models.database.migrations import Migrations
from app.models.database.memberships import Memberships
from app.models.database.licenses import Licenses


all_models = [Accounts, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions, OAuthClients, MFA, Discord, Webhooks, Requests, Migrations, Memberships, Licenses]

try:
    db.create_tables(all_models, safe=True)
except Exception as e:
    error(f"Failed to create tables: {e}")
