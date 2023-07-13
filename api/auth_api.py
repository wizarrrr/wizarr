from datetime import datetime, timedelta
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits

from flask import redirect, request, session
from flask_restx import Namespace, Resource
from werkzeug.security import check_password_hash, generate_password_hash

from api.helpers import try_catch
from models import Admins, Sessions

api = Namespace('Authentication', description='Authentication related operations', path="/auth")

@api.route('/login')
class Login(Resource):
    
    @try_catch
    def post(self):
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')

        user = Admins.select().where(Admins.username == username).first()

        # Check if the username is correct
        if user is None:
            warning("A user attempted to login with incorrect username: " + username)
            return {'error': 'Invalid Username or Password'}, 401

        # Check if the password is correct
        if not check_password_hash(user.password, password):
            warning("A user attempted to login with incorrect password: " + username)
            return {'error': 'Invalid Username or Password'}, 401

        # Migrate to scrypt from sha 256
        if user.password.startswith("sha256"):
            new_hash = generate_password_hash(password, method='scrypt')
            Admins.update(password=new_hash).where(Admins.username == username).execute()

        # Generate a new admin key and store it in the session
        key = ''.join(choices(ascii_uppercase + digits, k=20))

        session["admin"] = {
            "id": user.id,
            "username": user.username,
            "key": key
        }

        # Get IP address from request and User Agent from request
        ip_addr = request.headers.get("X-Forwarded-For") or request.remote_addr
        user_agent = request.user_agent.string

        # Expire length of session
        expire = None if remember else datetime.now() + timedelta(days=1)

        # Store the admin key in the database
        Sessions.create(session=key, user=user.id, ip=ip_addr, user_agent=user_agent, expires=expire)

        # Store the remember me setting in the session
        session.permanent = remember

        # Log the user in and redirect them to the homepage
        info(f"User successfully logged in the username {username}")
        return {'message': 'Login successful'}, 200

@api.route('/logout')
class Logout(Resource):
    
    @try_catch
    def post(self):
        # Delete the admin key from the session and database if it exists
        try:
            Sessions.delete().where(Sessions.session == session["admin"]["key"]).execute()
            session.pop("admin", None)
        except KeyError:
            pass

        # Redirect the user to the login page
        return {'message': 'Logout successful'}, 200