from models.database.accounts import Accounts
from models.database.api_keys import APIKeys
from models.database.base import db
from models.database.invitations import Invitations
from models.database.libraries import Libraries
from models.database.notifications import Notifications
from models.database.sessions import Sessions
from models.database.settings import Settings
from models.database.users import Users

all_models = [Accounts, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions]
db.create_tables([Accounts, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions], safe=True)
