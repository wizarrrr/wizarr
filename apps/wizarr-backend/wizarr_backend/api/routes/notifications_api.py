from logging import info

from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource

from app.notifications.exceptions import InvalidNotificationAgent
from app.models.notifications import NotificationsGetModel, NotificationsPostModel
from app.models.database.notifications import Notifications
from app.notifications.builder import get_web_resources, validate_resource

api = Namespace('Notifications', description='Notifications related operations', path="/notifications")

# api.add_model("NotificationsPostModel", NotificationsPostModel)
# api.add_model("NotificationsGetModel", NotificationsGetModel)

@api.route('')
@api.route('/', doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class NotificationsListAPI(Resource):
    """Notifications related operations"""

    method_decorators = [jwt_required()]

    def get(self, query=None) -> tuple[list[Notifications], int]:
        # Get all notifications from the database for the current user
        user_id = current_user['id']

        # Get all notifications for the current user
        notifications = Notifications.select().where(Notifications.user_id == user_id)
        responses = []

        # Loop through each notification
        for notification in notifications:
            # Validate the notification resource
            resource = validate_resource(notification.resource, notification.data)

            # Add the notification to the response
            response = resource.to_primitive()
            response['id'] = notification.id

            # Respond to query parameters
            query = request.args.get('query') or query

            # If query has , in it, split it into a list
            if query is not None and ',' in query:
                query = query.split(',')

            def get_query(query, resource, response):
                if not hasattr(resource, query): return

                # Get the attribute from the resource and add it to the response
                response[query] = getattr(resource, query)

                # If the attribute is a function, call it
                if callable(response[query]):
                    response[query] = response[query]()

            # If query is a list, loop through each query
            if query is not None and isinstance(query, list):
                for q in query:
                    get_query(q, resource, response)
            elif query is not None and isinstance(query, str):
                get_query(query, resource, response)

            # Add the response to the responses list
            responses.append(response)

        # Respond with all notifications for the current user
        return responses, 200

    def post(self) -> tuple[dict[str, str], int]:
        # Get the request body
        body = request.form

        # Make sure we have a resource
        if 'resource' not in body:
            return {"message": "Missing resource"}, 400

        # Get the notification resource
        resource = validate_resource(
            body.get('resource'),
            body
        )

        # Save the notification in the database
        resource.save()

        # Respond with the notification
        return resource.to_primitive(), 200


@api.route('/<int:notification_id>')
@api.route('/<int:notification_id>/', doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class NotificationsAPI(Resource):

    method_decorators = [jwt_required()]

    def delete(self, notification_id: int) -> tuple[dict[str, str], int]:
        # Get the notification from the database
        notification = Notifications.get_or_none(Notifications.id == notification_id)

        # If the notification does not exist, respond with a 404
        if notification is None:
            return {"message": "Notification does not exist"}, 404

        # If the notification does not belong to the current user, respond with a 403
        if str(notification.user_id) != str(current_user['id']):
            return {"message": "Notification does not belong to the current user"}, 403

        # Delete the notification from the database
        notification.delete_instance()

        # Respond with a 200
        return {"message": "Notification deleted successfully"}, 200


@api.route('/resources')
@api.route('/resources/', doc=False)
@api.doc(security=["jsonWebToken", "cookieAuth"])
class NotificationsResourcesAPI(Resource):
    """Get all notification resources"""

    def get(self) -> tuple[dict[str, str], int]:
        # Get all notification resources
        resources = get_web_resources()

        # Respond with all notification resources
        return resources, 200
