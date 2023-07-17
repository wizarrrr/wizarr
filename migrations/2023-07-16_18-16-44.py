from logging import error, migrations, warning

from peewee import *
from playhouse.migrate import *

from app import db
from app.exceptions import MigrationError

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    migrator = SqliteMigrator(db)

    # If Invitations table does not exist, return
    if not db.table_exists('invitations'):
        raise MigrationError('Invitations table does not exist')
    
    # If column plex_home already exists, return
    if 'plex_home' in [column.name for column in db.get_columns('invitations')]:
        return
    
    plex_home = BooleanField(null=True)  # Add Expires after update
    migrate(migrator.add_column('invitations', 'plex_home', plex_home))
    
    migrations("Added plex_home column to invitations table")