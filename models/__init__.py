from peewee import SqliteDatabase
from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field

from .admins import Admins, AdminsModel
from .apikeys import APIKeys, APIKeysModel
from .base import db
from .invitations import Invitations, InvitationsModel
from .libraries import Libraries, LibrariesModel
from .notifications import Notifications, NotificationsModel
from .sessions import Sessions, SessionsModel
from .settings import Settings, SettingsModel
from .users import Users, UsersModel

all_models = [Admins, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions]
db.create_tables([Admins, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions], safe=True)

class IdentityModel(PydanticBaseModel):
    id: int = Field(description="The ID of the path")