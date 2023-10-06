from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource
from playhouse.shortcuts import model_to_dict

from app.models.database.discord import Discord as DiscordDB

api = Namespace("Discord", description="OAuth related operations", path="/discord")

@api.route("/bot")
@api.route("/bot/", doc=False)
class Discord(Resource):
    """Discord related operations"""

    method_decorators = [jwt_required()]

    @api.doc(security="jwt")
    def get(self):
        """Get discord info"""
        data = DiscordDB.get()

        return model_to_dict(data), 200

    @api.doc(security="jwt")
    def post(self):
        """Update discord info"""
        # Get the discord token from the request
        token = request.form.get("token")
        enabled = request.form.get("enabled")

        # Check if the token is valid
        if not token or not enabled:
            return { "message": "Invalid data" }, 400

        # If first db entry, create it otherwise update it
        discord_bot, _ = DiscordDB.get_or_create(id=1)

        # Update the token
        discord_bot.token = token
        discord_bot.enabled = enabled in ["true", "True", "1"]

        # Save the entry
        discord_bot.save()

        return { "message": "Discord settings updated", "data": model_to_dict(discord_bot) }, 200
