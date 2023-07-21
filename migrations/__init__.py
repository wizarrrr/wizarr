import os
from datetime import datetime
from importlib import import_module
from logging import error, log, migrations

from app.exceptions import MigrationError
from models import *

# Do not attempt to change this file unless you know what you are doing
# as you could introduce arbitrary code execution on the server

def run():
    return

def migrate():
    # Log that migrations are starting
    migrations("STARTING MIGRATIONS")
    
    # Create a backup of the database
    datebase_dir = os.path.join(os.path.dirname(__file__), '../', 'database')
    
    # Create a backup of the database
    os.system(f'cp {datebase_dir}/database.db {datebase_dir}/database.temp')
    
    # Get migrations folder in base_dir
    migrations_dir = os.path.join(os.path.dirname(__file__), '../', 'migrations')
    
    # Function to rename temp backup to datetime.db if migrations fail
    def rename_temp():
        datetimename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        os.system(f'cp {datebase_dir}/database.temp {datebase_dir}/{datetimename}.db')
        
    # Error occured
    error_occured = False

    # Loop through all files in migrations folder based on date and time in filename
    for filename in sorted(os.listdir(migrations_dir)):
        
        # Only run python files in migrations folder
        if filename.endswith('.py'):
            
            # Import the module
            module = import_module(f'migrations.{filename[:-3]}')
            
            try:
                # Log that the migration is starting for this file
                # migrations(f'Running migration for {filename}')
                
                # Call the run function
                module.run()
                
            except MigrationError as e:
                print("\n")
                error("Error during migration, contact support on Discord, a database backup has been created in the database folder.")
                print("\n")
                error(f'Error: {e}')
                error(f'File: {os.path.realpath(os.path.join(migrations_dir, filename))}')
                print("\n")
                
                error_occured = True
                
            except Exception as e:
                # If an error occurs, log it with the filename and continue
                error(f'Error: {os.path.realpath(os.path.join(migrations_dir, filename))}')
                error(f'Message: {e}')
                
                error_occured = True
    
    # If an error occured, rename the temp backup to datetime.db
    if error_occured:
        from app import app
        if not app.debug:
            rename_temp()

    # Remove temp backup
    os.system(f'rm {datebase_dir}/database.temp')

    # Log that migrations are finished
    migrations("FINISHED MIGRATIONS")