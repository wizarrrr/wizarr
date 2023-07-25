from logging import migrations

from peewee import *
from peewee import CharField
from playhouse.migrate import *

from app import db
from app.exceptions import MigrationError

# Do not change the name of this file,
# migrations are run in order of their filenames date and time

# PLEASE USE migrations("MESSAGE HERE") FOR ANY INFO LOGGING
# Example: migrations("Creating table users")
# Feel free to use error and warning for any errors or warnings

def run():
    migrator = SqliteMigrator(db)

    # Add your migrations here
    if db.table_exists("users"):
        migrate(
            migrator.drop_not_null("users", "email"),
            migrator.drop_not_null("users", "code")
        )

        # Change all rows with empty strings to null
        db.execute_sql("UPDATE users SET email = NULL WHERE email = 'empty'")
        db.execute_sql("UPDATE users SET email = NULL WHERE email = ''")
        db.execute_sql("UPDATE users SET code = NULL WHERE code = 'empty'")
        db.execute_sql("UPDATE users SET code = NULL WHERE code = ''")
        migrations("Removed not null from users.email and users.code")
