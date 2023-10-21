import logging
from logging.handlers import WatchedFileHandler
from os import path
import coloredlogs
from definitions import DATABASE_DIR

# Configure the root logger
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

# Add a null handler to the root logger to prevent log messages from being discarded
logging.getLogger().addHandler(logging.NullHandler())

# Exclude certain messages from the logger with a filter
class ExcludeFilter(logging.Filter):
    def __init__(self, exclude_str):
        super().__init__()
        self.exclude_str = exclude_str

    def filter(self, record):
        return self.exclude_str not in record.getMessage()

class ExcludeLoggerFilter(logging.Filter):
    def __init__(self, exclude_logger):
        super().__init__()
        self.exclude_logger = exclude_logger

    def filter(self, record):
        return record.name != self.exclude_logger

# Get the root logger
logger = logging.getLogger()
werkzeug = logging.getLogger("werkzeug")

# Create a file handler for logging to a file
file_log_handler = WatchedFileHandler(path.join(DATABASE_DIR, "logs.log"), mode="a", encoding="utf-8")
file_log_handler.addFilter(ExcludeLoggerFilter("peewee"))
file_log_handler.addFilter(ExcludeFilter("socket.io"))
file_log_handler.setFormatter(coloredlogs.ColoredFormatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"))

# Add the file handler to the root logger
logger.addHandler(file_log_handler)

# Configure colored logging
coloredlogs.install(level=None, fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
coloredlogs.install(level=None, logger=werkzeug, fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

# Get a dictionary of all the loggers
loggers = logging.Logger.manager.loggerDict
# print(tabulate([[key, value] for key, value in loggers.items()], headers=["Logger", "Level"]))
logging.getLogger("socketio").setLevel(logging.ERROR)
