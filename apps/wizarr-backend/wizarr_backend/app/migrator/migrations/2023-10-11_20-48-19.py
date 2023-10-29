#
# CREATED ON VERSION: V3.4.2
# MIGRATION: 2023-10-11_20-48-19
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

    # Migrate old V2 settings to new V3 settings
    # Only run this migration if admin_username and admin_password exist in the settings table
    with db.transaction():
        if db.execute_sql("SELECT key FROM settings WHERE key = 'admin_username'").fetchone() and db.execute_sql("SELECT key FROM settings WHERE key = 'admin_password'").fetchone():
            # Get the old settings
            admin_username = db.execute_sql("SELECT value FROM settings WHERE key = 'admin_username'").fetchone()[0]
            admin_password = db.execute_sql("SELECT value FROM settings WHERE key = 'admin_password'").fetchone()[0]

            # Delete the old settings
            db.execute_sql("DELETE FROM settings WHERE key = 'admin_username'")
            db.execute_sql("DELETE FROM settings WHERE key = 'admin_password'")

            # Create the new account using the old credentials
            db.execute_sql(f"INSERT INTO accounts (username, password, role, tutorial) VALUES ('{admin_username}', '{admin_password}', 'admin', 0)")

    # Remove admin_key from the settings table
    with db.transaction():
        if db.execute_sql("SELECT key FROM settings WHERE key = 'admin_key'"):
                db.execute_sql("DELETE FROM settings WHERE key = 'admin_key'")

    # Only run this migration if request_type, request_url and request_api_key exist in the settings table
    with db.transaction():
        if db.execute_sql("SELECT key FROM settings WHERE key = 'request_type'").fetchone() and db.execute_sql("SELECT key FROM settings WHERE key = 'request_url'").fetchone() and db.execute_sql("SELECT key FROM settings WHERE key = 'request_api_key'").fetchone():
            # Get the old settings
            request_type = db.execute_sql("SELECT value FROM settings WHERE key = 'request_type'").fetchone()[0]
            request_url = db.execute_sql("SELECT value FROM settings WHERE key = 'request_url'").fetchone()[0]
            request_api_key = db.execute_sql("SELECT value FROM settings WHERE key = 'request_api_key'").fetchone()[0]

            # Delete the old settings
            db.execute_sql("DELETE FROM settings WHERE key = 'request_type'")
            db.execute_sql("DELETE FROM settings WHERE key = 'request_url'")
            db.execute_sql("DELETE FROM settings WHERE key = 'request_api_key'")

            # Create the new request using the old request data
            db.execute_sql(f"INSERT INTO requests (name, server_id, service, url, api_key) VALUES ('{request_type}', 1, '{request_type}', '{request_url}', '{request_api_key}')")

    # Only run this migration if api_key exists in the settings table
    with db.transaction():
        if db.execute_sql("SELECT key FROM settings WHERE key = 'api_key'").fetchone():
            # Rename the key from api_key to server_api_key in the settings table
            db.execute_sql("UPDATE settings SET key = 'server_api_key' WHERE key = 'api_key'")

    # Only run this migration if discord_id exist in the settings table
    with db.transaction():
        if db.execute_sql("SELECT key FROM settings WHERE key = 'discord_id'").fetchone():
            # Get the old settings
            discord_id = db.execute_sql("SELECT value FROM settings WHERE key = 'discord_id'").fetchone()[0]

            # Delete the old settings
            db.execute_sql("DELETE FROM settings WHERE key = 'discord_id'")
            db.execute_sql("DELETE FROM settings WHERE key = 'discord_widget'")

            # Create the new request using the old request data
            db.execute_sql(f"INSERT INTO discord (guild_id, enabled) VALUES ('{discord_id}', 1)")

    # Print a log to the console stating the migration has been run for this file
    print(f"MIGRATION: {__file__} run successfully")
    print("MIGRATION INFO: Upgrades people to V3.4.2")
