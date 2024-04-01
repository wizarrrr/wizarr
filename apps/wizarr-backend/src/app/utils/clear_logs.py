from flask_restx import Api
from json import dumps
from os import path
from definitions import DATABASE_DIR

def clear_logs():
    """Clear the logs.log file on startup"""
    base_dir = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))

    # Clear log file contents on startup
    if path.exists(path.join(DATABASE_DIR, "logs.log")):
        with open(path.join(DATABASE_DIR, "logs.log"), "w", encoding="utf-8") as f:
            f.write("")
