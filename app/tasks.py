from app import *
import logging
import datetime


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

# For all invitations, if the expires is not a string, make it a string
for invitation in Invitations.select():
    if invitation.expires == "None":
        invitation.expires = None
        invitation.save()
    elif type(invitation.expires) == str:
        invitation.expires = datetime.datetime.strptime(
            invitation.expires, "%Y-%m-%d %H:%M")
        invitation.save()


if not os.getenv("APP_URL") or os.getenv("APP_URL").endswith("/"):
    logging.error("APP_URL not set or wrong format. See docs for more info.")
    exit(1)
