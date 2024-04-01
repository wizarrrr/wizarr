from os import path, listdir
from importlib import import_module
from app.models.database.base import db
from app.models.database.migrations import Migrations
from packaging.version import parse
from datetime import datetime, timedelta
from os import environ
from definitions import LATEST_FILE
from sys import exit

def get_current_version():
    with open(LATEST_FILE, "r", encoding="utf-8") as f:
        current_version = str(f.read())
        return parse(current_version)

def get_current_database_version():
    # Get the current version from the database
    db_version = db.execute_sql("SELECT value FROM settings WHERE key = 'version';").fetchone()

    # If the version does not exist in the database then return 0.0.0
    if not db_version or not db_version[0]:
        return parse("0.0.0")

    return parse(db_version[0])

def run_migrations():
    # Log the start of the migration
    time = datetime.now()
    print("Starting migrations at", time.strftime("%Y-%m-%d %H:%M:%S"))

    # Get current version from the database and the current version from the version file
    # if it exists in the database
    db_version = get_current_database_version()
    current_version = get_current_version()

    # If the database version is greater than the current version then exit the application
    if db_version > current_version and not environ.get("WIZARR_FORCE_MIGRATION"):
        print("Database version is greater than the current version")
        print(f"Database version: {db_version}")
        print(f"Current version: {current_version}")
        print("Please update the application or set environment variable WIZARR_FORCE_MIGRATION to true to force the migration")
        exit(1)

    # Get the base directory
    BASE_DIR = path.abspath(path.join(path.dirname(path.realpath(__file__)), "../", "../"))
    MIGRATIONS_DIR = path.abspath(path.join(path.realpath(__file__), "../", "migrations"))

    # Get the current migrations in the database
    current_migrations = [migration.name for migration in Migrations.select()]

    # Run the migrations in the migrations folder based on their filenames date and time from oldest to newest
    for migration in sorted(listdir(MIGRATIONS_DIR)):
        # Skip if it does not end with .py
        if not migration.endswith(".py"):
            continue

        # Skip if it is already in the database
        if migration.split(".")[0] in current_migrations:
            continue

        # Import the migration
        print(f"Running migration {migration}")

        # Run the migration
        run_migration(migration.split(".")[0])

    # Update the database version
    update_database()

    # Log the end of the migration
    print("Finished migrations in", (datetime.now() - time).total_seconds(), "seconds")


def run_migration(name: str):
    # Import the migration
    try:
        migration = import_module(f"app.migrator.migrations.{name}")
    except Exception as e:
        print(f"Failed to import migration {name}")
        print(e)
        return

    # Run the migration
    try:
        migration.run()
    except Exception as e:
        print(f"Failed to run migration {name} on line {e.__traceback__.tb_lineno}")
        print(e)
        return

    # Save the migration to the database
    try:
        Migrations.create(name=name)
    except Exception as e:
        print(f"Failed to save migration {name} to the database")
        print(e)
        return


def update_database():
    # Get the current version
    current_version = get_current_version()

    # Get the current version from the database
    db_version = db.execute_sql("SELECT value FROM settings WHERE key = 'version';").fetchone()

    if not db_version or not db_version[0]:
        db.execute_sql(f"INSERT INTO settings (key, value) VALUES ('version', '{current_version}');")
    else:
        db.execute_sql(f"UPDATE settings SET value = '{current_version}' WHERE key = 'version';")
