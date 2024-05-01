from flask import request
from flask_restx import Namespace, Resource

from flask_socketio import join_room
from app.extensions import socketio
from os import urandom
from helpers.universal import global_invite_user_to_media_server

api = Namespace("Emby", description="Emby related operations", path="/emby")

@socketio.on("connect", namespace="/emby")
def connect():
    print("Client connected")

@api.route("")
@api.route("/", doc=False)
class EmbyStream(Resource):
    """Listen for Emby authentication events"""

    def post(self):
        # Get the username, password, code, and socket ID from the request
        username = request.form.get("username", None)
        email = request.form.get("email", None)
        password = request.form.get("password", None)
        code = request.form.get("code", None)
        socket_id = request.form.get("socket_id", None)

        # Check for missing Socket ID
        if socket_id is None:
            return { "message": "Missing socket ID" }, 400

        # Create a room with a random ID
        random_id = urandom(16).hex()
        join_room(random_id, sid=socket_id, namespace="/emby")

        # Send a message to the user and start a background task
        socketio.emit("message", f"Hello {username}!", namespace="/emby", to=socket_id)
        socketio.start_background_task(target=global_invite_user_to_media_server, username=username, email=email, password=password, code=code, socket_id=socket_id)

        # Return the room ID and the username
        return { "room": random_id, "username": username }, 200