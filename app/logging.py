import logging

from coloredlogs import install

# Create a logger object.
logger = logging.getLogger()

# Install the formatter
install(level=None, logger=logger, fmt='%(asctime)s %(levelname)s %(message)s')

# Add custom logging level to logger object
logging.addLevelName(50, "MIGRATIONS")
logging.addLevelName(60, "WEBPUSH")
logging.migrations = lambda msg, *args: logger._log(50, msg, args)
logging.webpush = lambda msg, *args: logger._log(60, msg, args)
