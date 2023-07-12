from datetime import datetime, timedelta
from logging import info, warning
from random import choices
from secrets import token_hex
from string import ascii_uppercase, digits

from flask import jsonify, make_response, redirect, render_template, request
from peewee import IntegrityError
from pydantic import BaseModel, Field, ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

from app import (Admins, APIKeys, Libraries, Notifications, Sessions, Settings,
                 session)
from app.exceptions import AuthorizationError
from app.helpers import scan_jellyfin_libraries
from app.notifications import notify_discord, notify_ntfy, notify_pushover
from app.partials import modal_partials, settings_partials


# All SETTINGS API routes
def get_settings():
    # Get all settings from the database
    settings = {
        setting.key: setting.value
        for setting in Settings.select()
    }

    # Return all settings and notification agents
    return settings

def post_settings(settings):
    # Verify settings data to prevent arbitrary sql injection
    # TODO: Add more verification
    
    # If discord_widget is empty or does not exist, set it to off
    try:
        if not settings.get("discord_widget"): settings["discord_widget"] = "off"
    except:
        pass
    
    # Update all settings in the database where the key is in settings
    for key, value in settings.items():
        Settings.get_or_create(key=key)
        Settings.update(value=value).where(Settings.key == key).execute()

        # Return the settings dictionary
    return settings

def get_setting(setting):
    # Return the setting from the database where the key is the setting parameter
    result = Settings.get_or_none(Settings.key == str(setting))

    if not setting or not result:
        return { "error": f"Setting {setting} not found" }

    # If the setting exists, return the setting dictionary
    return { setting: result.value }

def put_setting(setting, value):
    # Update setting in the database
    Settings.update(value=value).where(Settings.key == setting).execute()

    # Return the setting dictionary
    return {setting: value}

def delete_setting(setting):
    # Delete setting from the database
    Settings.delete().where(Settings.key == setting).execute()

    # Return the setting dictionary
    return {setting: None}


# All NOTIFICATIONS API routes
def get_notifications():
    # Get all notification agents from the database
    return list(Notifications.select().dicts())

def post_notifications(request):
    # Initialize variables for notification agent
    title = "Wizarr"
    message = "Wizarr here! Can you hear me?"
    tags = "tada"

    # Create object from form data
    form = {
        "agent_name": request.form.get("agent_name"),
        "agent_url": request.form.get("agent_url"),
        "agent_service": request.form.get("agent_service"),
        "agent_username": request.form.get("agent_username") or None,
        "agent_password": request.form.get("agent_password") or None
    }

    # Initialize object for functions to test notification agents
    notify_test = {
        "discord": lambda: notify_discord(message, form["agent_url"]),
        "ntfy": lambda: notify_ntfy(message, title, tags, form["agent_url"], form["agent_username"], form["agent_password"]),
        "pushover": lambda: notify_pushover(message, title, form["agent_url"], form["agent_username"], form["agent_password"]),
    }

        # Initialize object for functions to save notification agents
    notify_save = {
        "discord": lambda: Notifications.create(name=form["agent_name"], url=form["agent_url"], type=form["agent_service"]),
        "ntfy": lambda: Notifications.create(name=form["agent_name"], url=form["agent_url"], type=form["agent_service"], username=form["agent_username"], password=form["agent_password"]),
        "pushover": lambda: Notifications.create(name=form["agent_name"], url=form["agent_url"], type=form["agent_service"], userkey=form["agent_username"], apitoken=form["agent_password"]),
    }

    # Error function to return error modal with error message
    def error(error_msg):
        if request.headers.get("HX-Request"):
            response = make_response(modal_partials("create-notification-agent", error=error_msg))
            response.headers['HX-Retarget'] = '#create-modal'
            return response

        return { "error": error_msg }

    # Test notification agent and return error if it fails
    if not notify_test[form["agent_service"]]():
        return error("Could not connect to " + str(form["agent_service"]).capitalize())

    # Initialize variables by pulling function from object based on notification service
    notify_test_func = notify_test[form['agent_service']]
    notify_save_func = notify_save[form['agent_service']]

    # Run function to test notification agent and return error if it fails
    if not notify_test_func():
        return error(f"Could not connect to {str(form['agent_service']).capitalize()}")

    # Run function to save notification agent and log success
    notify_save_func()
    info("A user created a new notification agent")

    # Return success modal
    if request.headers.get("HX-Request"):
        return settings_partials("notifications")

    return { "success": "Notification agent created" }

def delete_notification(path_id):
    # Get notification agent from the database
    notification = Notifications.get_or_none(Notifications.id == path_id)

    # Return error if notification agent does not exist
    if not notification:
        return { "error": notification }

    # Delete notification agent from the database
    notification.delete_instance()
    
    return { "success": "Notification agent deleted" }



# All ACCOUNTS API routes
# TODO: Add account routes

# All ACCOUNTS SESSIONS API routes
def delete_accounts_session(admin_id, session_id):
    # Get the session from the database where the id is the path_id parameter
    db_session = Sessions.get_or_none(Sessions.id == session_id)
    current_user_id = session["admin"]["id"]
    
    # Check if the session exists and the user id matches the current user
    if not db_session or current_user_id != admin_id or db_session.user_id != current_user_id:
        return { "error": "Session not found" }
    
    # Delete the session from the database
    db_session.delete_instance()
    
    # Delete local session if it matches
    if session["admin"]["key"]  == session_id:
        try:
            session.pop("admin")
        except KeyError:
            pass
    
    return { "success": "Session deleted" }

# All ACCOUNTS API API routes
def get_accounts_api(admin_id):
    return

def post_accounts_api(id, data):
    class PostAccountsAPI(BaseModel):
        api_name: str = Field(..., min_length=3, max_length=50)
        admin_id: int
        
    try:
        # Validate form data
        PostAccountsAPI(**data, admin_id=id)
    
        # Get current user from the database and check the user matches the current user in session["admin"]["id"]
        current_user = Admins.get_or_none(Admins.id == id)
    
        # Return error if the user does not exist or the user id does not match the current user in session["admin"]["id"]
        if not current_user or current_user.id != session["admin"]["id"]:
            raise AuthorizationError("Could not authorize user to make this request")
    
        # Create API key
        api_key = token_hex(32)
    
        # Create API key in the database
        APIKeys.create(name=data["api_name"], key=api_key, user=current_user.id)
    
        return { "success": "API key created" }
    
    except ValidationError as e:
        return make_response(jsonify({ "error": e.errors() }), 422)
    except IntegrityError:
        return make_response(jsonify({ "error": "API key already exists" }), 400)
    except AuthorizationError as e:
        return make_response(jsonify({ "error": str(e) }), 401)
    except Exception as e:
        return make_response(jsonify({ "error": str(e) }), 500)

def delete_accounts_api(admin_id, api_id):
    return

def delete_accounts_api_id(admin_id, api_id):
    return



def get_libaries(request):
    # Get all libraries from the database
    libraries = [library for library in Libraries.select().dicts()]

    # Return libraries
    return libraries

def post_libraries(request):
    # Check required fields are present
    required = ["library_count", "server_type", "server_url", "server_api_key"]

    for field in required:
        if not request.form.get(field):
            return { "error": f"{field} is required" }

    # Get all libraries from the form
    library_count = int(request.form.get("library_count"))
    libraries = []

    # Take each library from the form and add it to the libraries list
    for i in range(library_count):
        libraries.append(request.form.get(f"library_{i + 1}"))

    # We need to scan the libraries for Jellyfin again to verify they exist and prevent arbitrary library IDs from being added
    def scan_jellyfin(libraries: list):
        jellyfin_libraries = scan_jellyfin_libraries(server_api_key=request.form.get("server_api_key"), server_url=request.form.get("server_url"))

        for library in jellyfin_libraries:
            if library["Id"] in libraries:
                try:
                    Libraries.get_or_create(id=library["Id"], name=library["Name"])
                except IntegrityError:
                    pass

    # If the server type is Jellyfin, scan the jellyfin libraries
    if request.form.get("server_type") == "jellyfin":
        scan_jellyfin(libraries)

    return { "success": "Libraries updated" }


def get_admin_users(request):
    username = Settings.get_or_create(key="admin_username")
    password = Settings.get_or_create(key="admin_password")

    return {
        "username": username[0].value,
        "password": password[0].value
    }

def post_admin_users(request):
    Admins.create(username=request.form.get("username"), password=generate_password_hash(request.form.get("password"), method='scrypt'))
    return { "success": "Admin user created" }

def login(username, password, remember):
    user = Admins.select().where(Admins.username == username).first()

    # Check if the username is correct
    if user is None:
        warning("A user attempted to login with incorrect username: " + username)
        return render_template("login.html", error="Invalid Username or Password")

    # Check if the password is correct
    if not check_password_hash(user.password, password):
        warning("A user attempted to login with incorrect password: " + username)
        return render_template("login.html", error="Invalid Username or Password")

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
    return redirect("/")

def logout():
    # Delete the admin key from the session and database if it exists
    try:
        Sessions.delete().where(Sessions.session == session["admin"]["key"]).execute()
        session.pop("admin", None)
    except KeyError:
        pass
    
    # Redirect the user to the login page
    return redirect("/login")

