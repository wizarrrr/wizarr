from logging import error, migrations, warning

from peewee import *
from playhouse.migrate import *

from app import db
from app.exceptions import MigrationError
from models.settings import Settings

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Check if Settings table exists
    if not db.table_exists('settings'):
        raise MigrationError('Settings table does not exist')
    
    # Add your migrations here
    if all(Settings.select().where(Settings.key == key).exists() for key in ['admin_username', 'plex_verified']):
        if not Settings.select().where(Settings.key == 'server_type').exists():
            
            plex_token = Settings.get(Settings.key == 'plex_token').value
            plex_url = Settings.get(Settings.key == 'plex_url').value
            plex_name = Settings.get(Settings.key == 'plex_name').value
            plex_libraries = Settings.get(Settings.key == 'plex_libraries').value
            
            Settings.create(key='server_type', value='plex')
            Settings.create(key='server_api_key', value=plex_token)
            Settings.delete().where(Settings.key == 'plex_token').execute()
            Settings.create(key='server_url', value=plex_url)
            Settings.delete().where(Settings.key == 'plex_url').execute()
            Settings.create(key='server_name', value=plex_name)
            Settings.delete().where(Settings.key == 'plex_name').execute()
            Settings.create(key='libraries', value=plex_libraries)
            Settings.delete().where(Settings.key == 'plex_libraries').execute()
            Settings.create(key='server_verified', value=Settings.get(Settings.key == 'plex_verified').value)
            Settings.delete().where(Settings.key == 'plex_verified').execute()
            
            migrations("Converted plex settings to global settings")