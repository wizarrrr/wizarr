from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.models.database.webhooks import Webhooks
from json import loads, dumps
from playhouse.shortcuts import model_to_dict
from datetime import datetime

api = Namespace('Webhooks', description='Webhooks related operations', path='/webhooks')

@api.route("")
class WebhooksListAPI(Resource):

    method_decorators = [jwt_required()]

    @api.doc(description="Get all webhooks")
    @api.response(200, "Successfully retrieved all webhooks")
    def get(self):
        """Get all webhooks"""
        response = list(Webhooks.select().dicts())
        return loads(dumps(response, indent=4, sort_keys=True, default=str)), 200

    @api.doc(description="Create a webhook")
    @api.response(200, "Successfully created a webhook")
    def post(self):
        """Create a webhook"""
        webhook = Webhooks.create(name=str(request.form.get("name")), url=str(request.form.get("url")))
        webhook.created = datetime.utcnow()
        return loads(dumps(model_to_dict(webhook), indent=4, sort_keys=True, default=str)), 200

@api.route("/<int:webhook_id>")
class WebhooksAPI(Resource):

    method_decorators = [jwt_required()]

    @api.doc(description="Get a single webhook")
    @api.response(200, "Successfully retrieved webhook")
    def get(self, webhook_id):
        """Get a single webhook"""
        webhook = Webhooks.get_or_none(Webhooks.id == webhook_id)
        if not webhook:
            return {"message": "Webhook not found"}, 404
        return loads(dumps(webhook, indent=4, sort_keys=True, default=str)), 200

    @api.doc(description="Delete a single webhook")
    @api.response(200, "Successfully deleted webhook")
    def delete(self, webhook_id):
        """Delete a single webhook"""
        webhook = Webhooks.get_or_none(Webhooks.id == webhook_id)
        if not webhook:
            return {"message": "Webhook not found"}, 404
        webhook.delete_instance()
        return {"message": "Webhook deleted"}, 200
