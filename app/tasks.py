# pylint: disable-all
import datetime
import logging
import logging.config

import requests

from app import *

# Migrations 1
try:
    migrator = SqliteMigrator(db)
    duration = CharField(null=True)  # Add Duration after update
    migrate(migrator.add_column('Invitations', 'duration', duration))
except Exception as e:
    logging.info(e)

# Add plex_allow_sync field
try:
    migrator = SqliteMigrator(db)
    plex_allow_sync = BooleanField(null=True)  # Add plex_allow_sync after update
    migrate(migrator.add_column('Invitations', 'plex_allow_sync', plex_allow_sync))
except Exception as e:
    logging.info(e)

# Migrations 2
try:
    migrator = SqliteMigrator(db)
    specific_libraries = CharField(null=True)  # Add Specific Libraries after update
    migrate(migrator.add_column('Invitations', 'specific_libraries', specific_libraries))
except Exception as e:
    logging.info(e)

# Migrations 3
try:
    migrator = SqliteMigrator(db)
    expires = DateTimeField(null=True)  # Add Expires after update
    migrate(migrator.add_column('Users', 'expires', expires))
except Exception as e:
    logging.info(e)

# For all invitations, if the expires is not a string, make it a string
for invitation in Invitations.select():
    if invitation.expires == "None":
        invitation.expires = None
        invitation.save()
    elif type(invitation.expires) == str:
        invitation.expires = datetime.datetime.strptime(
            invitation.expires, "%Y-%m-%d %H:%M")
        invitation.save()


# Make value nullable
try:
    migrator = SqliteMigrator(db)
    migrate(migrator.drop_not_null('Settings', 'value'))
except Exception as e:
    logging.info(e)

if not os.getenv("APP_URL"):
    logging.info("APP_URL not set or wrong format. See docs for more info.")
    exit(1)

LOGGING_CONFIG = {
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
        },
    },
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(levelname)s - %(message)s",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": os.getenv("LOG_LEVEL", "ERROR"),
            "propagate": True,
        },
    },
}

try:
    logging.config.dictConfig(LOGGING_CONFIG)
except Exception as e:
    logging.critical(f"Error in logging config, ignoring and using defaults. Error: {e}")

# Migrate from Plex to Global Settings:
if Settings.select().where(Settings.key == 'admin_username').exists():
    if Settings.select().where(Settings.key == 'plex_verified').exists():
        if not Settings.select().where(Settings.key == 'server_type').exists() :
            try:
                os.system("cp ./db/db.db ./db/1.6.5-db-backup.db")
                logging.info("db backup created due to major version update.")
            except:
                pass
            Settings.create(key='server_type', value='plex')
            Settings.create(key='server_api_key', value=Settings.get(Settings.key == 'plex_token').value)
            Settings.delete().where(Settings.key == 'plex_token').execute()
            Settings.create(key='server_url', value=Settings.get(Settings.key == 'plex_url').value)
            Settings.delete().where(Settings.key == 'plex_url').execute()
            Settings.create(key='server_name', value=Settings.get(Settings.key == 'plex_name').value)
            Settings.delete().where(Settings.key == 'plex_name').execute()
            Settings.create(key='libraries', value=Settings.get(Settings.key == 'plex_libraries').value)
            Settings.delete().where(Settings.key == 'plex_libraries').execute()
            Settings.create(key='server_verified', value=Settings.get(Settings.key == 'plex_verified').value)
            Settings.delete().where(Settings.key == 'plex_verified').execute()


# Migrations 4
try:
    migrator = SqliteMigrator(db)
    plex_home = BooleanField(null=True)  # Add Expires after update
    migrate(migrator.add_column('Invitations', 'plex_home', plex_home))
except Exception as e:
    logging.info(e)

# Migrations 5
try:
    if not Settings.select().where(Settings.key == 'server_api_key').exists():    
        settings = {
            settings.key: settings.value
            for settings in Settings.select()
        }

        try:
            os.system("cp ./db/db.db ./db/2.2.0-db-backup.db")
            logging.info("db backup created due to major version update.")
        except Exception as e:
            logging.info(e)

        try:
            # Migrate existing admin to new admin table
            Admins.get_or_create(username=settings.get("admin_username"), password=settings.get("admin_password"))
        except Exception as e:
            logging.info(e)

        try:
            # Migrate existing libraries to new libraries table
            if settings.get("server_type") == "jellyfin":
                libraries_array = settings.get("libraries").split(", ")

                headers = { "X-Emby-Token": settings.get("api_key") }
                response = requests.get(f"{settings.get('server_url')}/Library/MediaFolders", headers=headers, timeout=10)
                jellyfin_libraries = response.json()["Items"]

                for library in jellyfin_libraries:
                    if library["Id"] in libraries_array:
                        Libraries.get_or_create(id=library["Id"], name=library["Name"])

        except Exception as e:
            logging.info(e)
            
        try:
            #Migrate requests to new requests values
            overseerr_url = settings.get("overseerr_url")
            ombi_api_key = settings.get("ombi_api_key")
            
            Settings.create(key="request_url", value=overseerr_url)
            Settings.create(key="request_api_key", value=ombi_api_key)
            
        except Exception as e:
            logging.info(e)

        try:
            # Migrate api_key to server_api_key
            Settings.create(key="server_api_key", value=settings.get("api_key"))
        except Exception as e:
            logging.info(e)

        migrator = SqliteMigrator(db)
        
        # Users migration
        migrate(migrator.add_column('Users', 'auth', CharField(null=True, default=None)))
        migrate(migrator.add_column('Users', 'created', DateTimeField(null=True, default=None)))
        
        # Notifications migration
        migrate(migrator.add_column('Notifications', 'created', DateTimeField(null=True, default=None)))
        

        Settings.delete().where(Settings.key == 'admin_username').execute()
        Settings.delete().where(Settings.key == 'admin_password').execute()
        Settings.delete().where(Settings.key == 'admin_key').execute()
        Settings.delete().where(Settings.key == 'libraries').execute()
        Settings.delete().where(Settings.key == 'api_key').execute()
        Settings.delete().where(Settings.key == 'overseerr_url').execute()
        Settings.delete().where(Settings.key == 'ombi_api_key').execute()
        
        session.clear()

except Exception as e:
    logging.info(e)