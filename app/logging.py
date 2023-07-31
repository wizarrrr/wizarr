import logging

from coloredlogs import install

# Create a logger object.
logger = logging.getLogger()
app_logger = logging.getLogger(__name__)
werkzeug_logger = logging.getLogger("werkzeug")

# Install the formatter
install(level=None, logger=logger, fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
install(level=None, logger=werkzeug_logger, fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
# install(level=None, logger=werkzeug_logger, fmt="%(asctime)s %(levelname)s %(message)s")

# add filter to ignore /socket.io requests
werkzeug_logger.addFilter(lambda record: record.getMessage().find("/socket.io") <= -1)

# Add custom logging level to logger object
logging.addLevelName(50, "MIGRATIONS")
logging.addLevelName(60, "WEBPUSH")
# pylint: disable=protected-access
logging.migrations = lambda msg, *args: logger._log(50, msg, args)
logging.webpush = lambda msg, *args: logger._log(60, msg, args)


file_handler = logging.FileHandler("./database/logs.log")
logger.addHandler(file_handler)

# logger.setLevel(logging.ERROR)
logging.getLogger("socketio").setLevel(logging.ERROR)
logging.getLogger("engineio").setLevel(logging.ERROR)

logger.info("Logging started")
