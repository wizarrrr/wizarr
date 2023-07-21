from logging import error, migrations, warning

from peewee import *
from playhouse.migrate import *

from app import db
from app.exceptions import MigrationError

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    migrator = SqliteMigrator(db)
    
    if not db.table_exists('settings'):
        raise MigrationError('Settings table does not exist')

    with db.transaction():
        # Add your migrations here
        try:
            migrate(migrator.drop_not_null('settings', 'value'))
            migrations("Dropped not null constraint on settings")
        except OperationalError:
            migrations("Column 'value' already allows null values")
    