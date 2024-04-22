#
# CREATED ON VERSION: V4.0.0b8
# MIGRATION: 2024-04-22_19-17-37
# CREATED: Mon Apr 22 2024
#

from peewee import *
from playhouse.migrate import *

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time


def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)

    # Add new Column to users table called tutorial, its a boolean field with a default value of False
    with db.transaction():
        # Check if the column exists
        cursor = db.cursor()
        cursor.execute("PRAGMA table_info(invitations);")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        if "live_tv" not in column_names:
            db.execute_sql("ALTER TABLE invitations ADD COLUMN live_tv INTEGER")
        else:
            print("Column live_tv already exists")

    print("Migration 2024-04-22_19-17-37 complete")
