from logging import error, info, warning

from peewee import *
from playhouse.migrate import *

from app import db
from app.exceptions import MigrationError

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    migrator = SqliteMigrator(db)

    if not db.table_exists('users'):
        raise MigrationError('Users table does not exist')

    if 'expires' in [column.name for column in db.get_columns('users')]:
        return

    expires = DateTimeField(null=True)  # Add Expires after update
    migrate(migrator.add_column('Users', 'expires', expires))

    info("Added expires column to users table")