from app import *
import logging


# Migrations 1
try:
    migrator = SqliteMigrator(database)
    duration = CharField(null=True)  # Add Duration after update
    migrate(
        migrator.add_column('Invitations', 'duration', duration)
    )
except:
    pass


# Migrations 2
try:
    migrator = SqliteMigrator(database)
    specific_libraries = CharField(null=True)  # Add Duration after update
    migrate(
        migrator.add_column(
            'Invitations', 'specific_libraries', specific_libraries)
    )
except:
    pass

# Migrations 2
try:

    if ExpiringInvitations.used_by == IntegerField():
        migrator = SqliteMigrator(database)
        used_by = CharField(null=True)  # Add Duration after update
        migrate(
            migrator.drop_column('Invitations', 'used_by'),
            migrator.add_column('Invitations', 'used_by', used_by)
        )
except:
    pass


if not os.getenv("APP_URL"):
    logging.error("APP_URL not set")
    exit(1)