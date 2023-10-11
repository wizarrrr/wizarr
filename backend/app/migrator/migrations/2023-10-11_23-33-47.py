#
# CREATED ON VERSION: V3.4.2
# MIGRATION: 2023-10-11_23-33-47
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

    # Update all invitations libraries from there old name format to there id format
    with db.transaction():
        if db.execute_sql("SELECT id FROM invitations").fetchone() and db.execute_sql("SELECT id FROM libraries").fetchone():
            # Get all invitations
            invitations = db.execute_sql("SELECT id, specific_libraries FROM invitations").fetchall()

            # Get all libraries
            libraries = db.execute_sql("SELECT id, name FROM libraries").fetchall()

            print(invitations)
            print(libraries)

            # Loop through all invitations and update there libraries
            for invitation in invitations:
                # Get the old libraries
                old_libraries = invitation[1].split(", ")

                # Get the new libraries
                new_libraries = []
                for library in libraries:
                    if library[1] in old_libraries:
                        new_libraries.append(str(library[0]))

                # Update the libraries
                db.execute_sql(f"UPDATE invitations SET specific_libraries = '{','.join(new_libraries)}' WHERE id = {invitation[0]}")
