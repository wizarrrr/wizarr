#
# CREATED ON VERSION: V3.4.2
# MIGRATION: 2023-10-28_19-21-23
# CREATED: Sat Oct 28 2023
#

from peewee import *
from playhouse.migrate import *

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)

    # Add columns name server_id to requests table
    with db.transaction():
        # Check if the column exists
        cursor = db.cursor()
        cursor.execute("PRAGMA table_info(requests);")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        if 'name' not in column_names:
            db.execute_sql("ALTER TABLE requests ADD COLUMN name TEXT")
        else:
            print("Column name already exists")

        if 'server_id' not in column_names:
            db.execute_sql("ALTER TABLE requests ADD COLUMN server_id TEXT DEFAULT 0")
        else:
            print("Column server_id already exists")


    print("Migration 2023-10-28_19-21-23 complete")
