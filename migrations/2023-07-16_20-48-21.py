from datetime import datetime
from logging import migrations

from peewee import *
from playhouse.migrate import *

from app import db
from app.exceptions import MigrationError
from models.admins import Admins
from models.settings import Settings

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

# PLEASE USE migrations('MESSAGE HERE') FOR ANY INFO LOGGING
# Example: migrations('Creating table users')
# Feel free to use error and warning for any errors or warnings

def run():
    migrator = SqliteMigrator(db)

    # Add your migrations here
    if not db.table_exists('settings'):
        raise MigrationError('Settings table does not exist')
    
    settings = {
        settings.key: settings.value
        for settings in Settings.select()
    }
    
    if settings.get("admin_username", None) and settings.get("admin_password", None):
        Admins.get_or_create(username=settings.get("admin_username"), password=settings.get("admin_password"))
        Settings.delete().where((Settings.key == 'admin_username') | (Settings.key == 'admin_password') | (Settings.key == 'admin_key')).execute()
        migrations("Migrated admin credentials to Admins table")
        
    if settings.get("overseerr_url", None):
        Settings.create(key="request_url", value=settings.get("overseerr_url"))
        Settings.delete().where(Settings.key == 'overseerr_url').execute()
        migrations("Migrated overseerr_url to request_url")
        
    if settings.get("ombi_api_key", None):
        Settings.create(key="request_api_key", value=settings.get("ombi_api_key"))
        Settings.delete().where(Settings.key == 'ombi_api_key').execute()
        migrations("Migrated ombi_api_key to request_api_key")
        
    if settings.get("api_key", None):
        Settings.create(key="server_api_key", value=settings.get("api_key"))
        Settings.delete().where(Settings.key == 'api_key').execute()
        migrations("Migrated api_key to server_api_key")
        
    
    if 'auth' not in [column.name for column in db.get_columns('users')]:
        auth = CharField(null=True, default=None)
        migrate(migrator.add_column('users', 'auth', auth))
        
    if 'created' not in [column.name for column in db.get_columns('users')]:
        created = DateTimeField(null=True, default=datetime.now())
        migrate(migrator.add_column('users', 'created', created))
        
    if 'created' not in [column.name for column in db.get_columns('notifications')]:
        created = DateTimeField(null=True, default=datetime.now())
        migrate(migrator.add_column('notifications', 'created', created))
        
    if 'created' not in [column.name for column in db.get_columns('invitations')]:
        created = DateTimeField(null=True, default=datetime.now())
        migrate(migrator.add_column('invitations', 'created', created))
        
