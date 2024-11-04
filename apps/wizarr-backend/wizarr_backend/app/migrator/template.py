#
# CREATED ON VERSION: V{version}
# MIGRATION: {name}
# CREATED: {date}
#

from peewee import *
from playhouse.migrate import *

from app import db
from os import environ

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

def run():
    # Use migrator to perform actions on the database
    if environ.get('POSTGRES_ENABLED', 'false').lower() == 'true':
       migrator = PostgresqlMigrator(db)
    else:
        migrator = SqliteMigrator(db)
