from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field

from .admins import Admins
from .apikeys import APIKeys
from .base import db
from .invitations import Invitations
from .libraries import Libraries
from .notifications import Notifications
from .sessions import Sessions
from .settings import Settings
from .users import Users

all_models = [Admins, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions]
db.create_tables([Admins, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions], safe=True)

class IdentityModel(PydanticBaseModel):
    id: int = Field(description="The ID of the path")