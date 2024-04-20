#
# CREATED ON VERSION: V4.0.0b7
# MIGRATION: 2024-04-19_18-46-37
# CREATED: Fri Apr 19 2024
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

        if "sessions" not in column_names:
            db.execute_sql("ALTER TABLE invitations ADD COLUMN sessions INTEGER")
        else:
            print("Column sessions already exists")

    print("Migration 2024-04-19_18-46-37 complete")
