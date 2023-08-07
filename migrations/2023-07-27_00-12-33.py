from peewee import *
from playhouse.migrate import *
from logging import info

from app import db
from app.exceptions import MigrationError
from app.models.database.settings import Settings

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

# PLEASE USE info('MESSAGE HERE') FOR ANY INFO LOGGING
# Example: info('Creating table users')


def run():
    migrator = SqliteMigrator(db)

    # Add your migrations here
    # Settings table is two columns, key and value, if multiple rows have the same key the last one will be used and delete the others

    # Get all settings
    settings = Settings.select()

    # Check if the settings table is empty
    if len(settings) == 0:
        return

    # Get all settings that have the same key
    duplicate_settings = Settings.select().where(Settings.key.in_([setting.key for setting in settings])).group_by(Settings.key).having(fn.COUNT(Settings.key) > 1)

    # Check if there are any duplicate settings
    if len(duplicate_settings) == 0:
        return

    # Delete all duplicate settings
    for setting in duplicate_settings:
        setting.delete_instance()

    # Log that the duplicate settings were deleted
    info('Deleted duplicate settings')