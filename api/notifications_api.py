from datetime import datetime, timedelta
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits

from flask import make_response, redirect, request, session
from flask_restx import Namespace, Resource

from api.helpers import try_catch
from models import Notifications

api = Namespace('Notifications', description='Notifications related operations', path="/notifications")

@api.route('/')
class NotificationsListAPI(Resource):
    
    @try_catch
    def get(self) -> list[dict]:
        return list(Notifications.select().dicts())
    
    
    @try_catch
    def post(self) -> dict:
        # Import required modules
        from app import notifications
        from app.partials import modal_partials, settings_partials

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
            "discord": lambda: notifications.notify_discord(message, form["agent_url"]),
            "ntfy": lambda: notifications.notify_ntfy(message, title, tags, form["agent_url"], form["agent_username"], form["agent_password"]),
            "pushover": lambda: notifications.notify_pushover(message, title, form["agent_url"], form["agent_username"], form["agent_password"]),
        }

            # Initialize object for functions to save notification agents
        notify_save = {
            "discord": lambda: Notifications.create(name=form["agent_name"], url=form["agent_url"], type=form["agent_service"]),
            "ntfy": lambda: Notifications.create(name=form["agent_name"], url=form["agent_url"], type=form["agent_service"], username=form["agent_username"], password=form["agent_password"]),
            "pushover": lambda: Notifications.create(name=form["agent_name"], url=form["agent_url"], type=form["agent_service"], username=form["agent_username"], password=form["agent_password"]),
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
    

@api.route('/<int:notification_id>')
class NotificationsAPI(Resource):
    
    @try_catch
    def get(self, notification_id: int) -> dict:
        return Notifications.get_by_id(notification_id)
    
    
    @try_catch
    def delete(self, notification_id: int) -> dict:
        # Get notification agent from the database
        notification = Notifications.get_or_none(Notifications.id == notification_id)

        # Return error if notification agent does not exist
        if not notification:
            return { "error": notification }

        # Delete notification agent from the database
        notification.delete_instance()
    
        return { "success": "Notification agent deleted" }
