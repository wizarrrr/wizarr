from json import dumps, loads

from flask import request
from flask_jwt_extended import current_user, get_jti, get_jwt, jwt_required
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict
from datetime import datetime

from app.models.database.requests import Requests
from helpers.onboarding import showRequest

api = Namespace("Requests", description="Requests related operations", path="/requests")

@api.route('')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class RequestsListAPI(Resource):

    method_decorators = [jwt_required()]

    def get(self) -> tuple[list[dict[str, str]], int]:
        # Select all requests from the database
        requests = list(Requests.select().dicts())

        # Return the requests
        return loads(dumps(requests, indent=4, sort_keys=True, default=str)), 200

    def post(self) -> tuple[dict[str, str], int]:
        # Create the request
        request_db = Requests.create(**request.form)
        request_db.created = datetime.utcnow()
        showRequest(True)

        # Return the request
        return loads(dumps(model_to_dict(request_db), indent=4, sort_keys=True, default=str)), 200


@api.route('/<string:requests_id>')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class RequestsAPI(Resource):

    method_decorators = [jwt_required()]

    def get(self, requests_id: str) -> tuple[dict[str, str], int]:
        # Select the request from the database
        request = Requests.get(Requests.id == requests_id)

        return loads(dumps(request, indent=4, sort_keys=True, default=str)), 200

    def delete(self, requests_id: str) -> tuple[dict[str, str], int]:
        # Select the request from the database
        request = Requests.get(Requests.id == requests_id)

        # Delete the request
        request.delete_instance()

        # Check if there are no more requests in the database
        if Requests.select().count() == 0:
            showRequest(False)

        # Responnse
        response = { "message": f"Request { requests_id } has been deleted" }

        return response, 200
