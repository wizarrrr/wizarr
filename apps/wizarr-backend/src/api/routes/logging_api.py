from os import path, stat, linesep
from flask import send_file
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource
from io import BytesIO
from app.extensions import socketio
from termcolor import colored
from time import sleep
from definitions import DATABASE_DIR

api = Namespace("Logging", description="Logging related operations", path="/logging")
log_file = path.abspath(path.join(DATABASE_DIR, "logs.log"))
task = None

def watch_log_file(file_path):
    last_position = 0
    while True:
        with open(file_path, 'r', encoding='utf-8') as file:
            file.seek(last_position)
            new_lines = file.readlines()
            if new_lines:
                last_position = file.tell()
                for line in new_lines:
                    socketio.emit("log", line, namespace="/logging")
        sleep(0.1)

@socketio.on("connect", namespace="/logging")
@jwt_required()
def connect():
    socketio.emit("log", f"User {current_user['username']} connected to log stream.", namespace="/logging")
    socketio.start_background_task(watch_log_file, file_path=log_file)

@api.route("/text")
@api.route("/text/", doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class LogAPI(Resource):
    """API resource for downloading logs"""

    method_decorators = [jwt_required()]

    @staticmethod
    def get():
        with open(log_file, "rb") as f:
            log_data = f.read()

        log_data_io = BytesIO(log_data)

        return send_file(log_data_io, mimetype="text/plain")
