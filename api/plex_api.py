from threading import Thread

from flask import request
from flask_restx import Namespace, Resource
from plexapi.myplex import MyPlexAccount, Unauthorized
from requests import get

from flask_sse import ServerSentEvents

api = Namespace("Plex", description="Plex related operations", path="/plex")
sse = ServerSentEvents()


def test(code: str, token: str):
    try:
        get("https://hub.dummyapis.com/delay?seconds=2")
        sse.send(1, code, "step")
        get("https://hub.dummyapis.com/delay?seconds=2")
        sse.send(2, code, "step")
        get("https://hub.dummyapis.com/delay?seconds=2")
        sse.send(3, code, "step")
        sse.delete_announcer(code)
    except Exception as e:
        sse.delete_announcer(code)


@api.route("")
class Plex(Resource):
    """Start Plex authentication"""

    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        token = request.form.get("token", None)
        username = None

        try:
            username = MyPlexAccount(token).username
        except Unauthorized:
            return { "message": "Invalid token" }, 400

        code = sse.create_announcer()
        sse.send(username, code, "username")

        response = {"stream": code}

        Thread(target=test, args=(code, token)).start()

        return response, 200


@api.route("/<path:stream_id>")
class PlexStream(Resource):
    """Listen for Plex authentication events"""

    def get(self, stream_id):
        return sse.response(stream_id)
