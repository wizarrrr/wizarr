
from unittest import TestCase, mock

from flask import Response, make_response
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from peewee import IntegrityError, SqliteDatabase
from playhouse.shortcuts import model_to_dict
from pydantic import BaseModel, Field

from models.admins import Admins, AdminsGetModel, AdminsModel, AdminsPostModel
from models.sessions import Sessions

api = Namespace("Accounts", description="Accounts related operations", path="/accounts")

api.add_model("AdminsGetModel", AdminsGetModel)
api.add_model("AdminsPostModel", AdminsPostModel)

@api.route('')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class AccountsListAPI(Resource):
    
    method_decorators = [jwt_required()]

    @api.marshal_list_with(AdminsGetModel)
    @api.doc(description="Get all accounts")
    @api.response(200, "Successfully retrieved all accounts")
    @api.response(500, "Internal server error")
    def get(self) -> tuple[list[dict[str, str]], int]:
        # Select all admins from the database
        admins = Admins.select()
        
        # Remove the password from each admin
        response = [self._remove_password(admin) for admin in admins]
        
        return response, 200

    def _remove_password(self, admin: Admins) -> dict:
        # Convert the admin to a dictionary
        admin_dict: dict[str, str] = model_to_dict(admin)
        
        # Remove the password from the dictionary
        admin_dict.pop('password', None)
        
        return admin_dict


    @api.expect(AdminsPostModel)
    @api.marshal_with(AdminsGetModel)
    @api.doc(description="Create a new account")
    @api.response(200, "Successfully created a new account")
    @api.response(400, "Invalid account")
    @api.response(409, "Account already exists")
    @api.response(500, "Internal server error")
    def post(self) -> tuple[dict[str, str], int]:
        # TODO: Finish this function
        accounts: dict[str, str] = { key: value for key, value in self.request.form.items() }

        for username, password in accounts.items():
            Admins.create(username=username, password=password)

        response = AccountsAPI().get(username)
        
        return response, 200
    
    
@api.route('/<string:username>')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class AccountsAPI(Resource):
    
    method_decorators = [jwt_required()]

    @api.marshal_with(AdminsGetModel)
    @api.doc(description="Get an account")
    @api.response(200, "Successfully retrieved an account")
    @api.response(404, "Account not found")
    @api.response(500, "Internal server error")
    def get(self, username: str) -> Response:
        # Select the admin from the database with the given username
        admin = Admins.get(Admins.username == username)
        
        return make_response(self._remove_password(admin), 200)

    def _remove_password(self, admin: Admins) -> dict:
        # Convert the admin to a dictionary
        admin_dict: dict[str, str] = model_to_dict(admin)
        
        # Remove the password from the dictionary
        admin_dict.pop('password', None)
        
        return admin_dict
    
    
    @api.expect(AdminsPostModel)
    @api.marshal_with(AdminsGetModel)
    @api.doc(description="Update an account")
    @api.response(200, "Successfully updated an account")
    @api.response(400, "Invalid account")
    @api.response(404, "Account not found")
    @api.response(500, "Internal server error")
    def put(self, username: str) -> dict:
        # TODO: Finish this function
        class Put(BaseModel):
            data: dict[str, str] = Field(description="The account to update")

        account: dict[str, str] = { key: value for key, value in self.request.form.items() }

        Put(data=account)

        admin = Admins.get(Admins.username == username)
        admin.username = account['username']
        admin.password = account['password']
        admin.save()

        return self.get(admin.username)
