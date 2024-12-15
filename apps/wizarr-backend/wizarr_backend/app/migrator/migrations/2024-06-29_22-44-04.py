#
# CREATED ON VERSION: V4.1.1
# MIGRATION: 2024-06-29_22-44-04
# CREATED: Sat Jun 29 2024
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

        if "allow_download" not in column_names:
            db.execute_sql("ALTER TABLE invitations ADD COLUMN allow_download BOOLEAN DEFAULT 1")
        else:
            print("Column allow_download already exists")

    print("Migration 2024-06-29_22-44-04 complete")