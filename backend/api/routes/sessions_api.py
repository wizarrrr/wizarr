
from json import dumps, loads

from flask import request
from flask_jwt_extended import current_user, get_jti, jwt_required, get_jwt
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict

from app.models.database import Sessions

api = Namespace("Sessions", description="Sessions related operations", path="/sessions")

@api.route('')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class SessionsListAPI(Resource):

    method_decorators = [jwt_required()]

    def get(self) -> tuple[list[dict[str, str]], int]:
        # Select all sessions from the database
        sessions = list(Sessions.select().where(Sessions.user == current_user["id"]).dicts())

        # Return the sessions
        return loads(dumps(sessions, indent=4, sort_keys=True, default=str)), 200

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
        token = get_jwt()
        status = 401 if session.access_jti == token["jti"] else 200

        # Delete the session
        session.delete_instance()

        # Responnse
        response = { "message": f"Session { sessions_id } has been deleted" }

        return response, status
