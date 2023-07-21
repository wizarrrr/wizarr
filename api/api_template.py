from datetime import datetime, timedelta
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits

from flask import jsonify, make_response, redirect, request, session
from flask_jwt_extended import jwt_required
from flask_restx import Model, Namespace, Resource, fields
from playhouse.shortcuts import model_to_dict

api = Namespace('', description=' related operations', path="/")

@api.route('')
class Login(Resource):
    
    method_decorators = [jwt_required()]
    
    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        return

@api.route('/logout')
class Logout(Resource):
    
    method_decorators = [jwt_required()]

    @api.doc(description="")
    @api.response(500, "Internal server error")
    def post(self):
        return