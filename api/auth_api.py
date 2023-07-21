from datetime import datetime, timedelta
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits

from flask import jsonify, make_response, redirect, request, session
from flask_jwt_extended import (create_access_token, get_jti, jwt_required,
                                set_access_cookies, unset_jwt_cookies)
from flask_restx import Model, Namespace, Resource, fields
from playhouse.shortcuts import model_to_dict
from werkzeug.security import check_password_hash, generate_password_hash

from app.exceptions import AuthenticationError
from models import Admins, Sessions
from models.login import LoginModel, LoginPostModel

api = Namespace('Authentication', description='Authentication related operations', path="/auth")

api.add_model("LoginPostModel", LoginPostModel)

@api.route('/login')
class Login(Resource):
    
    method_decorators = []
    
    @api.expect(LoginPostModel)
    @api.doc(description="Login to the application")
    @api.response(200, "Login successful")
    @api.response(401, "Invalid Username or Password")
    @api.response(500, "Internal server error")
    def post(self):
        # Validate form data and initialize object for login
        form = LoginModel(
            username = request.form.get("username", None),
            password = request.form.get("password", None),
            remember = request.form.get("remember", False)
        )
        
        # Get the user from the database
        user = Admins.select().where(Admins.username == form.username).first()

        # Check if the username is correct
        if user is None:
            warning("A user attempted to login with incorrect username: " + form.username)
            raise AuthenticationError("Invalid Username or Password")

        # Check if the password is correct
        if not check_password_hash(user.password, form.password):
            warning("A user attempted to login with incorrect password: " + form.username)
            raise AuthenticationError("Invalid Username or Password")

        # Migrate to scrypt from sha 256
        if user.password.startswith("sha256"):
            new_hash = generate_password_hash(form.password, method='scrypt')
            Admins.update(password=new_hash).where(Admins.username == form.username).execute()

        # Expire length of session
        expire = False if form.remember else None
                
        # Generate a jwt token 
        token = create_access_token(identity=user.id, expires_delta=expire)
        jti = get_jti(token)
        
        # Get IP address from request and User Agent from request
        ip_addr = request.headers.get("X-Forwarded-For") or request.remote_addr
        user_agent = request.user_agent.string
        
        # Session expiry
        expiry = datetime.utcnow() + timedelta(days=30) if form.remember else datetime.utcnow() + timedelta(hours=1)
        
        # Store the admin key in the database
        Sessions.create(session=jti, user=user.id, ip=ip_addr, user_agent=user_agent, expires=expiry)
        
        # Create a response object
        response = jsonify({"msg": "Login successful", "user": model_to_dict(user, exclude=[Admins.password])})
        
        # Set the jwt token in the cookie
        set_access_cookies(response, token)
        
        # Log message and return response
        info(f"User successfully logged in the username {form.username}")
        return response

@api.route('/logout')
class Logout(Resource):
    
    method_decorators = [jwt_required(optional=True)]

    @api.doc(description="Logout the currently logged in user")
    @api.response(200, "Logout successful")
    @api.response(500, "Internal server error")
    def post(self):
        # Delete the session from the database
        token = request.cookies.get("access_token_cookie")
        session = Sessions.get(Sessions.session == get_jti(token))
        session.delete_instance()

        # Redirect the user to the login page
        response = jsonify({"msg": "Logout successful"})
        
        # Delete the jwt token from the cookie
        unset_jwt_cookies(response)
        
        # Log message and return response
        info(f"User successfully logged out")
        return response