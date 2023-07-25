
from unittest import TestCase, mock

from flask import Response, make_response, request
from flask_jwt_extended import get_jti, jwt_required
from flask_restx import Namespace, Resource
from peewee import IntegrityError, SqliteDatabase
from playhouse.shortcuts import model_to_dict

from models.database import Sessions

api = Namespace("Sessions", description="Sessions related operations", path="/sessions")

@api.route('')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class SessionsListAPI(Resource):

    method_decorators = [jwt_required()]

    def get(self) -> tuple[list[dict[str, str]], int]:
        # Select all sessions from the database
        sessions = Sessions.select()

        # Convert to array of dictionaries
        response = [model_to_dict(session) for session in sessions]

        return response, 200

@api.route('/<string:sessions_id>')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class SessionsAPI(Resource):

    method_decorators = [jwt_required()]

    def get(self, sessions_id: str) -> tuple[dict[str, str], int]:
        # Select the session from the database
        session = Sessions.get(Sessions.id == sessions_id)

        return model_to_dict(session), 200

    def delete(self, sessions_id: str) -> tuple[dict[str, str], int]:
        # Select the session from the database
        session = Sessions.get(Sessions.id == sessions_id)

        # If this session is the current session, return a 301 status code
        token = request.cookies.get("access_token_cookie")
        status = 301 if session.session == get_jti(token) else 200

        # Delete the session
        session.delete_instance()

        # Responnse
        response = { "msg": f"Session { sessions_id } has been deleted" }

        return response, status
