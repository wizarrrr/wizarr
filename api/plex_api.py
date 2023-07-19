from datetime import datetime, timedelta
from json import dumps
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits
from threading import Thread
from time import sleep

from flask import jsonify, make_response, redirect, request, session
from flask_restx import Model, Namespace, Resource, fields
from playhouse.shortcuts import model_to_dict
from plexapi.myplex import MyPlexAccount
from requests import get

from flask_sse import ServerSentEvents

api = Namespace('Plex', description=' related operations', path="/plex")
sse = ServerSentEvents()

def test(code: str, token: str):
    # Say hello to the user
    sse.send(MyPlexAccount(token).username, code, "username")
    
    get("https://hub.dummyapis.com/delay?seconds=2")
    sse.send(1, code, "step")
    get("https://hub.dummyapis.com/delay?seconds=2")
    sse.send(2, code, "step")
    get("https://hub.dummyapis.com/delay?seconds=2")
    sse.send(3, code, "step")
    
    sleep(3)
    sse.delete_announcer(code)

@api.route('')
class Plex(Resource):
        
    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        token = request.form.get("token", None)
        
        code = sse.create_announcer()
        
        response = { "stream": code }
        
        Thread(target=test, args=(code, token)).start()
        
        return response, 200
        
        
@api.route('/<path:stream_id>')
class PlexStream(Resource):
    
    def get(self, stream_id):
        return sse.response(stream_id)