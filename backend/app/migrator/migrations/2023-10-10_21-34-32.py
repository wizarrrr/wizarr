#
# CREATED ON VERSION: V3.4.2
# MIGRATION: 2023-10-10_21-34-32
# CREATED: Tue Oct 10 2023
#

from peewee import *
from playhouse.migrate import *
from datetime import datetime

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)

    # Add duration column to the invitations table with a default value of null
    # if the column already exists, do nothing
    with db.transaction():
        if "duration" not in [column.name for column in db.get_columns("invitations")]:
            migrate(migrator.add_column("invitations", "duration", CharField(default=None, null=True)))

    # Add plex_allow_sync column to the invitations table with a default value of false
    # if the column already exists, do nothing
    with db.transaction():
        if "plex_allow_sync" not in [column.name for column in db.get_columns("invitations")]:
            migrate(migrator.add_column("invitations", "plex_allow_sync", BooleanField(default=False)))

    # Add specific_libraries column to the invitations table with a default value of empty string
    # if the column already exists, do nothing
    with db.transaction():
        if "specific_libraries" not in [column.name for column in db.get_columns("invitations")]:
            migrate(migrator.add_column("invitations", "specific_libraries", CharField(default="")))

    # Add expires column to the users table with a default value of null
    # if the column already exists, do nothing
    with db.transaction():
        if "expires" not in [column.name for column in db.get_columns("users")]:
            migrate(migrator.add_column("users", "expires", DateTimeField(default=None, null=True)))

    # Add created column to the users table with a default value of current timestamp
    # if the column already exists, do nothing
    with db.transaction():
        if "created" not in [column.name for column in db.get_columns("users")]:
            migrate(migrator.add_column("users", "created", DateTimeField(null=True, default=datetime.now())))
            db.execute_sql("UPDATE users SET created = datetime('now') WHERE created IS NULL")

    # Fix code column from 'None' to null in the users table
    # if the column does not exist, do nothing
    with db.transaction():
        if "code" in [column.name for column in db.get_columns("users")]:
            migrate(migrator.drop_not_null("users", "code"))
            db.execute_sql("UPDATE users SET code = NULL WHERE code = 'None'")

    # Print a log to the console stating the migration has been run for this file
    print(f"MIGRATION: {__file__} run successfully")
    print("MIGRATION INFO: Upgrades people from all versions before 2.2.1")
