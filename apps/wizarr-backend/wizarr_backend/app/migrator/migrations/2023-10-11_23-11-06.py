#
# CREATED ON VERSION: V3.4.2
# MIGRATION: 2023-10-11_23-11-06
# CREATED: Wed Oct 11 2023
#

from peewee import *
from playhouse.migrate import *

from app import db

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    migrator = SqliteMigrator(db)

    # Move libraries from the settings table to the libraries table
    with db.transaction():
        if db.execute_sql("SELECT key FROM settings WHERE key = 'libraries'").fetchone():
            # Get the libraries from the settings table
            libraries = db.execute_sql("SELECT value FROM settings WHERE key = 'libraries'").fetchone()[0]

            from helpers.jellyfin import scan_jellyfin_libraries
            from helpers.plex import scan_plex_libraries

            # Get server_type, server_api_key and server_url from the settings table
            server_type = db.execute_sql("SELECT value FROM settings WHERE key = 'server_type'").fetchone()[0]
            server_url = db.execute_sql("SELECT value FROM settings WHERE key = 'server_url'").fetchone()[0]
            server_api_key = db.execute_sql("SELECT value FROM settings WHERE key = 'server_api_key'").fetchone()[0]

            # Decode the libraries variables
            old_libraries = libraries.split(", ")

            # Scan the libraries functions map
            scan_libraries = {
                "jellyfin": lambda: scan_jellyfin_libraries(server_api_key, server_url),
                "plex": lambda: scan_plex_libraries(server_api_key, server_url)
            }

            # Get the libraries from the server
            libraries = scan_libraries[server_type]()

            # Parse the libraries map
            parse_libraries = {
                "jellyfin": lambda: [{"id": library['Id'], "name": library['Name']} for library in libraries],
                "plex": lambda: [{"id": str(library.uuid), "name": library.title} for library in libraries]
            }

            # Parse the libraries
            new_libraries = parse_libraries[server_type]()

            # Add new libraries to database
            for new_library in new_libraries:
                if server_type == "jellyfin":
                    if new_library['id'] not in old_libraries:
                        print(f"Library {new_library['name']} not found in old libraries, skipping.")
                        continue

                    db.execute_sql(f"INSERT INTO libraries (id, name) VALUES ('{new_library['id']}', '{new_library['name']}')")
                    print(f"Library {new_library['name']} added to database.")
                elif server_type == "plex":
                    if new_library['name'] not in old_libraries:
                        print(f"Library {new_library['name']} not found in old libraries, skipping.")
                        continue

                    db.execute_sql(f"INSERT INTO libraries (id, name) VALUES ('{new_library['id']}', '{new_library['name']}')")
                    print(f"Library {new_library['name']} added to database.")


            # Remove old libraries from database
            db.execute_sql("DELETE FROM settings WHERE key = 'libraries'")


            # Print a log to the console stating the migration has been run for this file
            print(f"MIGRATION: {__file__} run successfully")
            print("MIGRATION INFO: Upgrades peoples libraries to V3")
