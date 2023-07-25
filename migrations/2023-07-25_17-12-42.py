from peewee import *
from playhouse.migrate import *
from logging import migrations

from app import db
from datetime import datetime
from models.database.accounts import Accounts

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

# PLEASE USE migrations('MESSAGE HERE') FOR ANY INFO LOGGING
# Example: migrations('Creating table users')
# Feel free to use error and warning for any errors or warnings


def run():
    migrator = SqliteMigrator(db)

    # Add your migrations here
    if db.table_exists("admins"):
        # Move all admins to accounts table
        for admin in db.execute_sql("SELECT * FROM admins"):
            Accounts.create(
                id=admin[0],
                username=admin[1],
                password=admin[2],
                email=admin[3],
                created=datetime.now()
            )

            migrations(f"Migrated {admin[1]} to accounts table")

        # Drop the admins table
        db.execute_sql("DROP TABLE admins")
