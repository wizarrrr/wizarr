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
    
    # If column plex_allow_sync already exists, return
    if 'plex_allow_sync' in [column.name for column in db.get_columns('invitations')]:
        return
    
    plex_allow_sync = BooleanField(null=True)  # Add plex_allow_sync after update
    migrate(migrator.add_column('invitations', 'plex_allow_sync', plex_allow_sync))
    
    migrations("Added plex_allow_sync column to invitations table")