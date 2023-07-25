from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field

from models.database.accounts import Accounts
from .apikeys import APIKeys
from .base import db
from .invitations import Invitations
from .libraries import Libraries
from .notifications import Notifications
from .sessions import Sessions
from .settings import Settings
from .users import Users

from .jellyfin.user import JellyfinUser

all_models = [Accounts, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions]
db.create_tables([Accounts, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions], safe=True)

class IdentityModel(PydanticBaseModel):
    id: int = Field(description="The ID of the path")