#
# CREATED ON VERSION: V{version}
# MIGRATION: {name}
# CREATED: {date}
#

from peewee import Model, SqliteDatabase, PostgresqlDatabase
from os import environ

if environ.get('POSTGRES_ENABLED', 'false').lower() == 'true':
    required_vars = ['POSTGRES_DATABASE', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASS']
    
    missing_vars = [var for var in required_vars if not environ.get(var)]
    if missing_vars:
        raise EnvironmentError(f"The following environment variables are missing : {', '.join(missing_vars)}")

    db = PostgresqlDatabase(
        environ['POSTGRES_DATABASE'],
        user=environ['POSTGRES_USER'],
        password=environ['POSTGRES_PASS'],
        host=environ['POSTGRES_HOST'],
        port=int(environ['POSTGRES_PORT']) 
    )
else:
    db = SqliteDatabase("./database/database.db")

class BaseModel(Model):
    class Meta:
        database = db
        