from flask import request
from flask_restx import Namespace, Resource
from plexapi.myplex import MyPlexAccount, Unauthorized

from flask_socketio import join_room
from app.extensions import socketio
from os import urandom
from helpers.universal import global_invite_user_to_media_server

api = Namespace("Plex", description="Plex related operations", path="/plex")

@socketio.on("connect", namespace="/plex")
def connect():
    print("Client connected")

@api.route("")
@api.route("/", doc=False)
class PlexStream(Resource):
    """Listen for Plex authentication events"""

    def post(self):
        # Get the token from the request
        token = request.form.get("token", None)
        code = request.form.get("code", None)
        socket_id = request.form.get("socket_id", None)

        # Check both the token and the socket ID
        if token is None or socket_id is None:
            return { "message": "Missing token or socket ID" }, 400

        # Check if the token is valid
        try:
            username = MyPlexAccount(token=token).username
        except Unauthorized:
            return { "message": "Invalid token" }, 400

        # Create a room with a random ID
        random_id = urandom(16).hex()
        join_room(random_id, sid=socket_id, namespace="/plex")

        # Send a message to the user and start a background task
        socketio.emit("message", f"Hello {username}!", namespace="/plex", to=socket_id)
        socketio.start_background_task(target=global_invite_user_to_media_server, token=token, code=code, socket_id=socket_id)

        # Return the room ID and the username
        return { "room": random_id, "username": username }, 200
