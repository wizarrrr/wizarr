def OAuth() -> dict:
    # Import the required modules
    from flask_pyoidc.provider_configuration import ProviderMetadata, ClientMetadata, ProviderConfiguration
    from models.database.oauth import OAuth as OAuthDatabase

    # Get all OAuth providers from the database
    oauth_providers: list[OAuthDatabase] = OAuthDatabase.select()

    # Create a dictionary of providers
    providers = {}

    # Loop through each provider and add it to the dictionary
    for provider in oauth_providers:

        # Create a client metadata object
        client_metadata = ClientMetadata(
            client_id=provider.client_id,
            client_secret=provider.client_secret,
            post_logout_redirect_uris=["/logout"]
        )

        # Create a provider metadata object
        provider_metadata = ProviderMetadata(
            issuer=provider.issuer,
            authorization_endpoint=provider.authorization_endpoint,
            token_endpoint=provider.token_endpoint,
            userinfo_endpoint=provider.userinfo_endpoint
        )

        # Create a provider configuration object
        provider_configuration = ProviderConfiguration(
            client_metadata=client_metadata,
            provider_metadata=provider_metadata
        )

        # Add the provider configuration to the dictionary
        providers[provider.issuer] = provider_configuration


    # Return providers
    return providers
