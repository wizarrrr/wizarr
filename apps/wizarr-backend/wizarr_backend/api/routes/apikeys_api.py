from flask import request
from flask_jwt_extended import jwt_required, current_user, create_access_token, get_jti
from flask_restx import Namespace, Resource
from app.models.database.api_keys import APIKeys
from json import loads, dumps
from playhouse.shortcuts import model_to_dict
from datetime import datetime

api = Namespace('API Keys', description='API Keys related operations', path='/apikeys')

@api.route("")
class APIKeysListAPI(Resource):

    method_decorators = [jwt_required()]

    @api.doc(description="Get all API Keys")
    @api.response(200, "Successfully retrieved all API Keys")
    def get(self):
        """Get all API Keys"""
        response = list(APIKeys.select().where(APIKeys.user_id == current_user['id']).dicts())
        return loads(dumps(response, indent=4, sort_keys=True, default=str)), 200

    @api.doc(description="Create an API Key")
    @api.response(200, "Successfully created an API Key")
    def post(self):
        """Create an API Key"""
        token = create_access_token(fresh=False, identity=current_user['id'], expires_delta=False)
        jti = get_jti(encoded_token=token)

        api_key = APIKeys.create(
            name=str(request.form.get("name")),
            key=str(token),
            jti=str(jti),
            user_id=str(current_user['id'])
        )

        response = model_to_dict(APIKeys.get(APIKeys.id == api_key))
        return loads(dumps(response, indent=4, sort_keys=True, default=str)), 200

@api.route("/<int:api_key_id>")
class APIKeysAPI(Resource):

    method_decorators = [jwt_required()]

    @api.doc(description="Get a single API Key")
    @api.response(200, "Successfully retrieved API Key")
    def get(self, api_key_id):
        """Get a single API Key"""
        api_key = APIKeys.get_or_none(APIKeys.id == api_key_id and APIKeys.user_id == current_user['id'])
        if not api_key:
            return {"message": "API Key not found"}, 404
        return loads(dumps(model_to_dict(api_key), indent=4, sort_keys=True, default=str)), 200

    @api.doc(description="Delete a single API Key")
    @api.response(200, "Successfully deleted API Key")
    def delete(self, api_key_id):
        """Delete a single API Key"""
        api_key = APIKeys.get_or_none(APIKeys.id == api_key_id and APIKeys.user_id == current_user['id'])
        if not api_key:
            return {"message": "API Key not found"}, 404
        api_key.delete_instance()
        return {"message": "API Key deleted"}, 200
