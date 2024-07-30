#
# CREATED ON VERSION: V4.1.1
# MIGRATION: 2024-07-30_11-02-04
# CREATED: Tue Jul 30 2024
#

from peewee import *
from playhouse.migrate import *

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)

    # Create new table 'onboarding'
    with db.transaction():
        # Check if the table exists
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='onboarding';")
        table_exists = cursor.fetchone()

        if not table_exists:
            db.execute_sql("""
                CREATE TABLE "onboarding" (
                    "id" INTEGER NOT NULL UNIQUE,
                    "value" TEXT NOT NULL,
                    "order" INTEGER NOT NULL UNIQUE,
                    "enabled" INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY("id")
                )
            """)
            print("Table 'onboarding' created successfully")
        else:
            print("Table 'onboarding' already exists")

    print("Migration 2024-07-30_11-02-04 complete")
