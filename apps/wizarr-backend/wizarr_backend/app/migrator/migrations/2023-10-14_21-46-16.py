#
# CREATED ON VERSION: V3.4.2
# MIGRATION: 2023-10-14_21-46-16
# CREATED: Sat Oct 14 2023
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
        cursor.execute("PRAGMA table_info(accounts);")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        if 'tutorial' not in column_names:
            db.execute_sql("ALTER TABLE accounts ADD COLUMN tutorial BOOLEAN DEFAULT 0")
        else:
            print("Column tutorial already exists")

    print("Migration 2023-10-14_21-46-16 complete")
