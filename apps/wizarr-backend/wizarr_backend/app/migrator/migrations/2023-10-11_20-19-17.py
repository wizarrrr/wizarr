#
# CREATED ON VERSION: V3.4.2
# MIGRATION: 2023-10-11_20-19-17
# CREATED: Wed Oct 11 2023
#

from peewee import *
from playhouse.migrate import *

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)


    # Update all rows in the invitations table that have expires columns with textual "None" to actual None
    # if the column does not exist, do nothing
    with db.transaction():
        db.execute_sql("UPDATE invitations SET expires = NULL WHERE expires = 'None'")

    # Drop all values in the settings table that are not null
    with db.transaction():
        migrate(migrator.drop_not_null("settings", "value"))

    # Print a log to the console stating the migration has been run for this file
    print(f"MIGRATION: {__file__} run successfully")
    print("MIGRATION INFO: Upgrades people from all versions on 2.2.1")
