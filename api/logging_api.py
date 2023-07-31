from os import path
from flask import send_file
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource
from flask_socketio import join_room
from io import BytesIO
from app.extensions import socketio
from os import urandom
from termcolor import colored

api = Namespace("Logging", description="Logging related operations", path="/logging")
log_file = path.abspath(path.join(path.dirname(__file__), "../", "database", "logs.log"))

last_modified_time = None
last_position = 0
task = None

def read_file_if_changed():
    global last_modified_time
    global last_position

    while True:
        try:
            modified_time = path.getmtime(log_file)
        except FileNotFoundError:
            modified_time = None

        if modified_time != last_modified_time:
            last_modified_time = modified_time

            with open(log_file, "r", encoding="utf-8") as f:
                f.seek(last_position)
                new_lines = f.readlines()
                last_position = f.tell()

            for line in new_lines:
                socketio.emit("log", line, namespace="/logging")

@socketio.on("connect", namespace="/logging")
@jwt_required()
def start_logging():
    global task
    socketio.emit("log", colored(f"{current_user['username']} connected to the log stream\n", "yellow"), namespace="/logging")
    # start background task unless it's already running
    if not task or not task.is_alive():
        task = socketio.start_background_task(target=read_file_if_changed)
    print(task, task.is_alive() if task else None)

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
