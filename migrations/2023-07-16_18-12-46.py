from datetime import datetime
from logging import error, info, warning

from peewee import *
from playhouse.migrate import *

from app import db
from app.exceptions import MigrationError
from models.database.invitations import Invitations

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Check if Invitations table exists
    if not db.table_exists('invitations'):
        raise MigrationError('Invitations table does not exist')

    didRun = False

    # Add your migrations here
    for invitation in Invitations.select():
        if invitation.expires == "None":
            invitation.expires = None
            invitation.save()
            didRun = True
        elif type(invitation.expires) == str:
            invitation.expires = datetime.strptime(invitation.expires, "%Y-%m-%d %H:%M")
            invitation.save()
            didRun = True

    if didRun:
        info("Converted expires column to datetime or None")