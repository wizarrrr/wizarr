from flask import send_file
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict

from helpers.jellyfin import get_jellyfin_profile_picture
from models.users import Users

from app.extensions import cache

api = Namespace("Users", description="Users related operations", path="/users")

@api.route("")
class UsersListAPI(Resource):

    method_decorators = [jwt_required()]

    @api.doc(description="Get all users in the database")
    @api.response(500, "Internal server error")
    def get(self):
        # Select all users from the database
        users = Users.select()

        # Convert the users to a list of dictionaries
        response = [model_to_dict(user) for user in users]

        return response, 200


    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        return


@api.route("/<string:user_id>/profile-picture")
class UsersProfilePictureAPI(Resource):

    method_decorators = [jwt_required()]

    @cache.cached(timeout=3600)
    @api.doc(description="Get a user profile picture")
    @api.response(500, "Internal server error")
    def get(self, user_id):
        picture = get_jellyfin_profile_picture(user_id)
        return send_file(picture, mimetype="image/jpeg")
