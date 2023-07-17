from datetime import datetime, timedelta
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits

from flask import jsonify, make_response, redirect, request, session
from flask_jwt_extended import jwt_required
from flask_restx import Model, Namespace, Resource, fields
from playhouse.shortcuts import model_to_dict

from models.users import Users

api = Namespace('Users', description='Users related operations', path="/users")

@api.route('/')
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



@api.route('/logout')
class UsersAPI(Resource):
    
    method_decorators = [jwt_required()]

    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        return