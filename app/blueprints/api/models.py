"""OpenAPI models for Flask-RESTX API documentation."""

from flask_restx import fields

from app.extensions import api

# Status Models
status_model = api.model(
    "Status",
    {
        "users": fields.Integer(description="Total number of users"),
        "invites": fields.Integer(description="Total number of invitations"),
        "pending": fields.Integer(description="Number of pending invitations"),
        "expired": fields.Integer(description="Number of expired invitations"),
    },
)

# User Models
user_model = api.model(
    "User",
    {
        "id": fields.Integer(description="User ID"),
        "username": fields.String(description="Username"),
        "email": fields.String(description="Email address"),
        "server": fields.String(description="Media server name"),
        "server_type": fields.String(
            description="Type of media server (plex, jellyfin, etc.)"
        ),
        "expires": fields.DateTime(description="Expiration date (ISO format)"),
        "created": fields.DateTime(description="Creation date (ISO format)"),
    },
)

user_list_model = api.model(
    "UserList",
    {
        "users": fields.List(fields.Nested(user_model)),
        "count": fields.Integer(description="Total number of users"),
    },
)

user_extend_request = api.model(
    "UserExtendRequest",
    {
        "days": fields.Integer(
            description="Number of days to extend (default: 30)", default=30
        ),
    },
)

user_extend_response = api.model(
    "UserExtendResponse",
    {
        "message": fields.String(description="Success message"),
        "new_expiry": fields.DateTime(description="New expiration date"),
    },
)

# Invitation Models
invitation_model = api.model(
    "Invitation",
    {
        "id": fields.Integer(description="Invitation ID"),
        "code": fields.String(description="Invitation code"),
        "url": fields.String(description="Ready-to-use invitation URL"),
        "status": fields.String(
            description="Invitation status", enum=["pending", "used", "expired"]
        ),
        "created": fields.DateTime(description="Creation date (ISO format)"),
        "expires": fields.DateTime(description="Expiration date (ISO format)"),
        "used_at": fields.DateTime(description="Date when invitation was used"),
        "used_by": fields.String(description="Username who used the invitation"),
        "duration": fields.String(
            description='User access duration in days or "unlimited"'
        ),
        "unlimited": fields.Boolean(description="Whether user access is unlimited"),
        "specific_libraries": fields.List(
            fields.Integer, description="Specific library IDs if restricted"
        ),
        "display_name": fields.String(description="Display name for the invitation"),
        "server_names": fields.List(fields.String, description="List of server names"),
        "uses_global_setting": fields.Boolean(
            description="Whether display name comes from global setting"
        ),
    },
)

invitation_list_model = api.model(
    "InvitationList",
    {
        "invitations": fields.List(fields.Nested(invitation_model)),
        "count": fields.Integer(description="Total number of invitations"),
    },
)

invitation_create_request = api.model(
    "InvitationCreateRequest",
    {
        "server_ids": fields.List(
            fields.Integer,
            required=False,
            description="Array of server IDs (required, but validated by API for better error messages)",
        ),
        "expires_in_days": fields.Integer(
            description="Days until invitation expires (1, 7, 30, or null)",
            enum=[1, 7, 30],
        ),
        "duration": fields.String(
            description='User access duration in days or "unlimited"',
            default="unlimited",
        ),
        "unlimited": fields.Boolean(
            description="Whether user access is unlimited", default=True
        ),
        "library_ids": fields.List(
            fields.Integer, description="Array of library IDs to grant access to"
        ),
        "allow_downloads": fields.Boolean(
            description="Allow user downloads", default=False
        ),
        "allow_live_tv": fields.Boolean(
            description="Allow live TV access", default=False
        ),
        "allow_mobile_uploads": fields.Boolean(
            description="Allow mobile uploads", default=False
        ),
    },
)

invitation_create_response = api.model(
    "InvitationCreateResponse",
    {
        "message": fields.String(description="Success message"),
        "invitation": fields.Nested(invitation_model),
    },
)

# Library Models
library_model = api.model(
    "Library",
    {
        "id": fields.Integer(description="Library ID"),
        "name": fields.String(description="Library name"),
        "external_id": fields.String(
            description="External library ID from media server"
        ),
        "server_id": fields.Integer(description="Server ID this library belongs to"),
        "server_name": fields.String(description="Server name this library belongs to"),
        "enabled": fields.Boolean(description="Whether this library is enabled"),
    },
)

library_list_model = api.model(
    "LibraryList",
    {
        "libraries": fields.List(fields.Nested(library_model)),
        "count": fields.Integer(description="Total number of libraries"),
    },
)

# Server Models
server_model = api.model(
    "Server",
    {
        "id": fields.Integer(description="Server ID"),
        "name": fields.String(description="Server name"),
        "server_type": fields.String(
            description="Server type (plex, jellyfin, emby, etc.)"
        ),
        "server_url": fields.String(description="Internal server URL"),
        "external_url": fields.String(description="External server URL"),
        "verified": fields.Boolean(description="Whether server connection is verified"),
        "allow_downloads": fields.Boolean(description="Whether downloads are allowed"),
        "allow_live_tv": fields.Boolean(description="Whether live TV is allowed"),
        "allow_mobile_uploads": fields.Boolean(
            description="Whether mobile uploads are allowed"
        ),
        "created_at": fields.DateTime(description="Server creation date"),
    },
)

server_list_model = api.model(
    "ServerList",
    {
        "servers": fields.List(fields.Nested(server_model)),
        "count": fields.Integer(description="Total number of servers"),
    },
)

# API Key Models
api_key_model = api.model(
    "ApiKey",
    {
        "id": fields.Integer(description="API key ID"),
        "name": fields.String(description="API key name"),
        "created_at": fields.DateTime(description="Creation date"),
        "last_used_at": fields.DateTime(description="Last used date"),
        "created_by": fields.String(description="Username who created the key"),
    },
)

api_key_list_model = api.model(
    "ApiKeyList",
    {
        "api_keys": fields.List(fields.Nested(api_key_model)),
        "count": fields.Integer(description="Total number of API keys"),
    },
)

# Error Models
error_model = api.model(
    "Error",
    {
        "error": fields.String(description="Error message"),
    },
)

success_message_model = api.model(
    "SuccessMessage",
    {
        "message": fields.String(description="Success message"),
    },
)
