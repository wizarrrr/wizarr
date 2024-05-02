from flask import send_file
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from json import loads, dumps

from helpers.universal import global_sync_users_to_media_server, global_delete_user_from_media_server
from app.models.database.users import Users

from app.extensions import cache

api = Namespace("Users", description="Users related operations", path="/users")

@api.route("")
class UsersListAPI(Resource):

    method_decorators = [jwt_required()]

    @api.doc(description="Get all users in the database")
    @api.response(500, "Internal server error")
    def get(self):
        # Select all users from the database
        response = list(Users.select().dicts())
        return loads(dumps(response, indent=4, sort_keys=True, default=str)), 200


    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        return


@api.route("/<string:user_id>")
class UsersAPI(Resource):

    method_decorators = [jwt_required()]

    @api.doc(description="Delete a user from the database and media server")
    @api.response(500, "Internal server error")
    def delete(self, user_id):
        return global_delete_user_from_media_server(user_id), 200


@api.route("/scan")
class UsersScanAPI(Resource):

    method_decorators = [jwt_required()]

    @api.doc(description="Scan for new users")
    @api.response(500, "Internal server error")
    def get(self):
        return global_sync_users_to_media_server(), 200

