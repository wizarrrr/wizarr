#
# CREATED ON VERSION: V4.1.0b1
# MIGRATION: 2024-05-03_22-33-10
# CREATED: Fri May 03 2024
#

from peewee import *
from playhouse.migrate import *

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)

    # Remove column plex_home from invitations table
    with db.transaction():
        # Check if the column exists
        cursor = db.cursor()
        cursor.execute("PRAGMA table_info(invitations);")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        if "plex_home" in column_names:
            # drop the column plex_home
            db.execute_sql("ALTER TABLE invitations DROP COLUMN plex_home")
        else:
            print("Column plex_home already dropped")

    print("Migration 2024-05-03_22-33-10 complete")