from schematics.models import Model
from schematics.types import StringType

from models.database.oauth_clients import OAuthClients

class OAuthModel(Model):
    """OAuth Model for OAuth Clients"""

    # ANCHOR - OAuth Clients Model
    name = StringType(required=False, default=None)
    issuer = StringType(required=True)
    consumer_key = StringType(required=False, default=None)
    consumer_secret = StringType(required=False, default=None)
    request_token_params = StringType(required=False, default=None)
    request_token_url = StringType(required=False, default=None)
    access_token_method = StringType(required=False, default=None)
    access_token_url = StringType(required=False, default=None)
    authorize_url = StringType(required=False, default=None)
    userinfo_endpoint = StringType(required=False, default=None)


    # ANCHOR - Create OAuth Client in the database
    def create_oauth_client(self):
        # Serialize the OAuth Client data to a dictionary
        oauth_client = self.to_native()

        # Create the OAuth Client in the database
        OAuthClients.create(**oauth_client)

        # Return the OAuth Client
        return self.to_native()

    # ANCHOR - Update OAuth Client in the database
    # TODO: Update OAuth Client in the database
