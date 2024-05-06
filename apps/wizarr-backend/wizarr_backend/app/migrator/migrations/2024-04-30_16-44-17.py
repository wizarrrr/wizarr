#
# CREATED ON VERSION: V4.0.0
# MIGRATION: 2024-04-30_16-44-17
# CREATED: Tue Apr 30 2024
#

from peewee import *
from playhouse.migrate import *

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)

    # Add new Column to users table, its a boolean field with a default value of True
    with db.transaction():
        # Check if the column exists
        cursor = db.cursor()
        cursor.execute("PRAGMA table_info(invitations);")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        if "hide_user" not in column_names:
            db.execute_sql("ALTER TABLE invitations ADD COLUMN hide_user BOOLEAN DEFAULT 1")
        elif "live_tv" in column_names:
            db.execute_sql("ALTER TABLE invitations ALTER COLUMN live_tv SET DATA TYPE BOOLEAN;")
        else:
            print("Column hide_user already exists")

    print("Migration 2024-04-30_16-44-17 complete")