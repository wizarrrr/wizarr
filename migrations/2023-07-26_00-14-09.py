from peewee import *
from playhouse.migrate import *
from logging import migrations

from app import db
from app.exceptions import MigrationError

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

# PLEASE USE migrations('MESSAGE HERE') FOR ANY INFO LOGGING
# Example: migrations('Creating table users')
# Feel free to use error and warning for any errors or warnings

def run():
    migrator = SqliteMigrator(db)

    # Add your migrations here
    if not db.table_exists("settings"):
        raise MigrationError("Table settings does not exist")

    # Check if settings key is unique
    if not db.execute_sql("SELECT DISTINCT value FROM settings"):
        raise MigrationError("settings key is not unique")

    # Check if settings key is unique
    query = db.execute_sql("SELECT COUNT(DISTINCT key) FROM settings")
    unique_keys = query.fetchone()[0]
    total_rows = db.execute_sql("SELECT COUNT(*) FROM settings").fetchone()[0]

    if unique_keys != total_rows:
        migrate(migrator.add_unique("settings", "key"))
        migrations("Added unique constraint to settings key")
