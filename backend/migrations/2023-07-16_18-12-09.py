from logging import error, info, warning

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

    # If column specific_libraries already exists, return
    if 'specific_libraries' in [column.name for column in db.get_columns('invitations')]:
        return

    specific_libraries = CharField(null=True)  # Add Specific Libraries after update
    migrate(migrator.add_column('invitations', 'specific_libraries', specific_libraries))

    info("Added specific_libraries column to invitations table")