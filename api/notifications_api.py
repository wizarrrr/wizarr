from datetime import datetime, timedelta
from logging import info, warning
from random import choices
from string import ascii_uppercase, digits

from flask import Response, make_response, redirect, request, session
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields
from peewee import IntegrityError

from app.exceptions import InvalidNotificationAgent
from models import IdentityModel
from models.notifications import (Notifications, NotificationsGetModel,
                                  NotificationsModel, NotificationsPostModel)

api = Namespace('Notifications', description='Notifications related operations', path="/notifications")

api.add_model("NotificationsPostModel", NotificationsPostModel)
api.add_model("NotificationsGetModel", NotificationsGetModel)

@api.route('/')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class NotificationsListAPI(Resource):
    
    method_decorators = [jwt_required()]

    @api.marshal_list_with(NotificationsGetModel)
    @api.doc(description="Get all notifications")
    @api.response(200, "Notifications retrieved successfully")
    @api.response(500, "Internal server error")
    def get(self) -> tuple[list[Notifications], int]:
        # Get all notifications from the database
        response = list(Notifications.select().dicts())
        
        return response, 200
    
    
    @api.expect(NotificationsPostModel)
    @api.marshal_with(NotificationsGetModel)
    @api.doc(description="Create a new notification agent")
    @api.response(201, "Notification created successfully")
    @api.response(400, "Invalid notification agent")
    @api.response(409, "Notification agent already exists")
    @api.response(500, "Internal server error")
    def post(self) -> tuple[Notifications, int]:
        # Import required modules
        from app import notifications

        # Initialize variables for notification agent
        title = "Wizarr"
        message = "Wizarr here! Can you hear me?"
        tags = "tada"

        # Validate form data and initialize object for notification agent        
        form = NotificationsModel(
            name     = request.form.get("name", None),
            url      = request.form.get("url", None),
            type     = request.form.get("type", None),
            username = request.form.get("username", None),
            password = request.form.get("password", None)
        )

        # Initialize object for functions to test notification agents
        notify_test = {
            "discord": lambda: notifications.notify_discord(message, form.url),
            "ntfy": lambda: notifications.notify_ntfy(message, title, tags, form.url, form.username, form.password),
            "pushover": lambda: notifications.notify_pushover(message, title, form.url, form.username, form.password),
        }

        # Initialize object for functions to save notification agents
        notify_save = {
            "discord": lambda: Notifications.create(name=form.name, url=form.url, type=form.type),
            "ntfy": lambda: Notifications.create(name=form.name, url=form.url, type=form.type, username=form.username, password=form.password),
            "pushover": lambda: Notifications.create(name=form.name, url=form.url, type=form.type, username=form.username, password=form.password),
        }

        # Initialize variables by pulling function from object based on notification service
        notify_test_func = notify_test[form.type]
        notify_save_func = notify_save[form.type]

        # Run function to test notification agent and return error if it fails
        if not notify_test_func():
            raise InvalidNotificationAgent(f"Notification agent {form.name} failed test")

        # Run function to save notification agent
        notification = notify_save_func()
        
        if not notification:
            raise InvalidNotificationAgent(f"Notification agent {form.name} failed to save")
        
        # Log new notification agent creation
        info("A user created a new notification agent")
        
        # Respond with new notification agent
        response = Notifications.get_by_id(notification.id)
        
        return response, 201
    

@api.route('/<int:notification_id>')
@api.doc(security=["jsonWebToken", "cookieAuth"])
class NotificationsAPI(Resource):

    method_decorators = [jwt_required()]

    @api.marshal_with(NotificationsGetModel)
    @api.doc(description="Get a notification agent by ID")
    @api.response(200, "Notification retrieved successfully")
    @api.response(400, "Invalid notification ID")
    @api.response(404, "Notification agent not found")
    @api.response(500, "Internal server error")
    def get(self, notification_id: int) -> tuple[Notifications, int]:
        # Validate notification ID and return error if it fails
        form = IdentityModel(id=notification_id)
        
        # Get notification agent from the database
        response = Notifications.get_or_none(form.id)
        
        # Raise error if notification agent does not exist
        if not response:
            raise InvalidNotificationAgent(f"Notification agent {form.id} not found")
        
        return response, 200
    
    
    @api.doc(description="Update a notification agent by ID")
    @api.response(200, "Notification agent deleted successfully")
    @api.response(400, "Invalid notification ID")
    @api.response(404, "Notification agent not found")
    @api.response(500, "Internal server error")
    def delete(self, notification_id: int) -> tuple[dict[str, str], int]:
        # Validate notification ID and return error if it fails
        form = IdentityModel(id=notification_id)
        
        # Get notification agent from the database
        notification = Notifications.get_or_none(Notifications.id == form.id)

        # Return error if notification agent does not exist
        if not notification:
            raise InvalidNotificationAgent(f"Notification agent {form.id} not found")

        # Delete notification agent from the database
        notification.delete_instance()
        
        # Respond with success
        response = { "msg": f"Notification agent {form.id} deleted successfully" }
    
        return response, 200
