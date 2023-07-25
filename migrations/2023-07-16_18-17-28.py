from logging import migrations
from typing import Optional

from peewee import *
from playhouse.migrate import *

from app import db
from app.exceptions import MigrationError
from models.database.libraries import Libraries
from models.database.settings import Settings

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # If table Libraries, Settings does not exist, raise error
    if not db.table_exists("libraries") or not db.table_exists("settings"):
        raise MigrationError("Libraries or Settings table does not exist")

    settings = {
        settings.key: settings.value
        for settings in Settings.select()
    }

    if settings.get("libraries", None):

        # Import required helpers
        from helpers.plex import scan_plex_libraries
        from helpers.jellyfin import scan_jellyfin_libraries

        # Get Server settings
        server_type = settings.get("server_type")
        server_url = settings.get("server_url")
        server_api_key = settings.get("server_api_key", None) or settings.get("api_key")

        # Get libraries from settings
        old_libraries: list[str] = settings.get("libraries").split(", ")
        new_libraries: Optional[list[dict]] = None

        if server_type == "jellyfin":
            libraries = scan_jellyfin_libraries(server_api_key, server_url)
            new_libraries = [{"id": library['Id'], "name": library['Name']} for library in libraries]

        elif server_type == "plex":
            libraries = scan_plex_libraries(server_api_key, server_url)
            new_libraries = [{"id": str(library.uuid), "name": library.title} for library in libraries]

        else:
            migrations("Server type not supported.")
            return

        # Check if libraries are valid
        if not new_libraries:
            migrations("No libraries found.")
            return

        # Check if libraries are valid
        if server_type == "jellyfin":

            # Add old libraries to database if they are in the new libraries
            for new_library in new_libraries:
                if new_library['id'] not in old_libraries:
                    migrations(f"Library {new_library['name']} not found in old libraries, skipping.")
                    continue

                # Add library to database
                Libraries.get_or_create(id=new_library['id'], name=new_library['name'])
                migrations(f"Library {new_library['name']} added to database.")

        elif server_type == "plex":

            # Add old libraries to database if they are in the new libraries
            for new_library in new_libraries:
                if new_library['name'] not in old_libraries:
                    migrations(f"Library {new_library['name']} not found in old libraries, skipping.")
                    continue

                # Add library to database
                Libraries.get_or_create(id=new_library['id'], name=new_library['name'])
                migrations(f"Library {new_library['name']} added to database.")

        # Delete old libraries from database
        Settings.delete().where(Settings.key == "libraries").execute()


        migrations("Deleted old libraries from database.")
