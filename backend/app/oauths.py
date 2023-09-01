from app import app, oauth
from app.models.database.oauth_clients import OAuthClients
from requests import get

oauth_database: OAuthClients = OAuthClients.select()
remote_apps = []

for oauth_db in oauth_database:
    remote_app = oauth.remote_app(
        name=oauth_db.issuer,
        consumer_key=oauth_db.consumer_key,
        consumer_secret=oauth_db.consumer_secret,
        request_token_url=oauth_db.request_token_url,
        access_token_method=oauth_db.access_token_method,
        access_token_url=oauth_db.access_token_url,
        authorize_url=oauth_db.authorize_url
    )

    remote_apps.append(remote_app)


for provider in remote_apps:
    @app.route(f'/oauth/{provider.name}/login')
    def oauth_login(oauth_provider=provider):
        return oauth_provider.authorize(callback=f"{app.config['PREFERRED_URL_SCHEME']}://{app.config['SERVER_NAME']}/oauth/{oauth_provider.name}/callback")

for provider in remote_apps:
    @app.route(f'/oauth/{provider.name}/callback')
    def oauth_callback(oauth_provider=provider):
        resp = oauth_provider.authorized_response()
        access_token = resp["access_token"]

        user = get('https://api.github.com/user', headers={"Authorization": f"Bearer {access_token}"})
        return user.json()
