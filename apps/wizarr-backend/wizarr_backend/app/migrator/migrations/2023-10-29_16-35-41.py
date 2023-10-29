#
# CREATED ON VERSION: V3.4.2
# MIGRATION: 2023-10-29_16-35-41
# CREATED: Sun Oct 29 2023
#

from peewee import *
from playhouse.migrate import *

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)

    # Add columns auth to users table
    with db.transaction():
        # Check if the column exists
        cursor = db.cursor()
        cursor.execute("PRAGMA table_info(users);")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        if 'auth' not in column_names:
            db.execute_sql("ALTER TABLE users ADD COLUMN auth TEXT")
        else:
            print("Column auth already exists")

    print("Migration 2023-10-29_16-35-41 complete")
