from datetime import datetime
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits

from flask import make_response, redirect, render_template
from peewee import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app import Admins, Libraries, Notifications, Settings, session
from app.helpers import scan_jellyfin_libraries
from app.notifications import notify_discord, notify_ntfy, notify_pushover
from app.partials import modal_partials, settings_partials


def get_settings():
    # Get all settings from the database
    settings = {
        setting.key: setting.value
        for setting in Settings.select()
    }

    # Return all settings and notification agents
    return settings

def post_settings(settings):
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



def get_notifications(request):
    if request.headers.get("HX-Request"):
        # Return settings partial for notifications
        return settings_partials("notifications")

    # Get all notification agents from the database
    return list(Notifications.select().dicts())

def post_notifications(request):
    # Initialize variables for notification agent
    title = "Wizarr"
    message = "Wizarr here! Can you hear me?"
    tags = "tada"

    # Create object from form data
    form = {
        "name": request.form.get("name"),
        "url": request.form.get("url"),
        "notification_service": request.form.get("notification_service"),
        "username": request.form.get("username") or None,
        "password": request.form.get("password") or None,
        "userkey": request.form.get("userkey") or None, # (Pushover only) TODO: Make this use username
        "apitoken": request.form.get("apitoken") or None # (Pushover only) TODO: Make this use password
    }

    # Initialize object for functions to test notification agents
    notify_test = {
        "discord": lambda: notify_discord(message, form["url"]),
        "ntfy": lambda: notify_ntfy(message, title, tags, form["url"], form["username"], form["password"]),
        "pushover": lambda: notify_pushover(message, title, form["url"], form["userkey"], form["apitoken"]),
    }

        # Initialize object for functions to save notification agents
    notify_save = {
        "discord": lambda: Notifications.create(name=form["name"], url=form["url"], type=form["notification_service"]),
        "ntfy": lambda: Notifications.create(name=form["name"], url=form["url"], type=form["notification_service"], username=form["username"], password=form["password"]),
        "pushover": lambda: Notifications.create(name=form["name"], url=form["url"], type=form["notification_service"], userkey=form["userkey"], apitoken=form["apitoken"]),
    }

    # Error function to return error modal with error message
    def error(error_msg):
        if request.headers.get("HX-Request"):
            response = make_response(modal_partials("create-notification-agent", error=error_msg))
            response.headers['HX-Retarget'] = '#create-modal'
            return response

        return { "error": error_msg }

    # Test notification agent and return error if it fails
    if not notify_test[form["notification_service"]]():
        return error("Could not connect to " + str(form["notification_service"]).capitalize())

    # Initialize variables by pulling function from object based on notification service
    notify_test_func = notify_test[form['notification_service']]
    notify_save_func = notify_save[form['notification_service']]

    # Run function to test notification agent and return error if it fails
    if not notify_test_func():
        return error(f"Could not connect to {str(form['notification_service']).capitalize()}")

    # Run function to save notification agent and log success
    notify_save_func()
    info("A user created a new notification agent")

    # Return success modal
    if request.headers.get("HX-Request"):
        return settings_partials("notifications")

    return { "success": "Notification agent created" }

def delete_notification(request, path_id):
    # Get notification agent from the database
    notification = Notifications.get_or_none(Notifications.id == path_id)

    def error(error_msg):
        if request.headers.get("HX-Request"):
            response = make_response(modal_partials("delete-notification-agent", error=error_msg))
            response.headers['HX-Retarget'] = '#delete-modal'
            return response

        return { "error": error_msg }

    # Return error if notification agent does not exist
    if not notification:
        return error("Notification agent not found")

    # Delete notification agent from the database
    notification.delete_instance()

    # Return success message
    if request.headers.get("HX-Request"):
        return settings_partials("notifications")

    return { "success": "Notification agent deleted" }



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
    user = Admins.get_or_none(Admins.username == username)

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

    session["admin_key"] = key
    session["admin_username"] = username

    # Store the admin key in the database
    Admins.update(session=key).where(Admins.username == username).execute()

    # Store the remember me setting in the session
    session.permanent = not remember

    # Log the user in and redirect them to the homepage
    info(f"User successfully logged in the username {username}")
    return redirect("/")

def logout():
    # Delete the admin key from the session
    session.pop("admin_key", None)

    # Redirect the user to the login page
    return redirect("/login")
