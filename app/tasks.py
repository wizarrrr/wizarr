from app import *
import datetime
import logging, logging.config



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
    specific_libraries = CharField(null=True)  # Add Specific Libraries after update
    migrate(
        migrator.add_column(
            'Invitations', 'specific_libraries', specific_libraries)
    )
except:
    pass

# Migrations 3
try:
    migrator = SqliteMigrator(database)
    expires = DateTimeField(null=True)  # Add Expires after update
    migrate(
        migrator.add_column(
            'Users', 'expires', expires)
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


if not os.getenv("APP_URL"):
    logging.error("APP_URL not set or wrong format. See docs for more info.")
    exit(1)

LOGGING_CONFIG = {
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
        },
    },
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(levelname)s - %(message)s",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": os.getenv("LOG_LEVEL", "ERROR"),
            "propagate": True,
        },
    },
}

try:
    logging.config.dictConfig(LOGGING_CONFIG)
except:
    logging.critical("Error in logging config, ignoring")