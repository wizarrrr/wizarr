from peewee import SqliteDatabase

from .admins import Admins
from .apikeys import APIKeys
from .base import db
from .invitations import Invitations
from .libraries import Libraries
from .notifications import Notifications
from .sessions import Sessions
from .settings import Settings
from .users import Users

db.create_tables([Admins, APIKeys, Invitations, Libraries, Notifications, Settings, Users, Sessions], safe=True)
