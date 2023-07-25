from flask_jwt_extended import current_user

from models.database import APIKeys


# TODO: MOVE THIS TO AN API ENDPOINT
def get_api_keys():
    # Get all API keys from the database
    admin_api_keys = list(
        APIKeys.select().where(APIKeys.user == current_user["id"]).execute()
    )

    # Return all API keys
    return admin_api_keys
