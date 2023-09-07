from os import getenv, environ

from dotenv import load_dotenv
from flask import Flask
# from sentry_sdk.integrations.flask import FlaskIntegration
# from sentry_sdk.integrations.asyncio import AsyncioIntegration
# from sentry_sdk import init as sentry_init

from api import *
from migrations import migrate

from .config import create_config
from .extensions import *
from .models.database import *
from .security import *
from .utils.babel_locale import get_locale
from .utils.clear_logs import clear_logs

BASE_DIR = path.abspath(path.dirname(__file__))

# Load environment variables
load_dotenv()

# Create the app
app = Flask(__name__)

# Initialize Sentry
# sentry_init(
#     dsn="https://95cc1c69bfea93ce8502e26b519cd318@o4505748808400896.ingest.sentry.io/4505748886716416",
#     integrations=[
#         FlaskIntegration(),
#         AsyncioIntegration()
#     ],
#     profiles_sample_rate=1.0,
#     traces_sample_rate=1.0,
#     environment="development" if app.debug else "production"
# )

# Override Flask server name if it contains http or https
if getenv("APP_URL") and getenv("APP_URL", "").startswith("http://") or getenv("APP_URL", "").startswith("https://"):
    host = getenv("APP_URL").replace("http://", "").replace("https://", "")
    app.config["SERVER_NAME"] = host
    environ["APP_URL"] = host

# Run database migrations scripts
if not app.debug or getenv("MIGRATE"):
    migrate()

app.config.update(**create_config(app))
schedule.authenticate(lambda auth: auth is not None)

# Initialize App Extensions
sess.init_app(app)
jwt.init_app(app)
cache.init_app(app)
api.init_app(app)
schedule.init_app(app)
socketio.init_app(app, async_mode="gevent" if app.config["GUNICORN"] else "threading", cors_allowed_origins="*", async_handlers=True)
oauth.init_app(app)

@socketio.on("ping")
def ping():
    socketio.emit("pong")

# Clear cache on startup
with app.app_context():
    cache.clear()
    clear_logs()

# Register Flask blueprints
# app.after_request(refresh_expiring_jwts)
# app.before_request(check_enviroment)

# Register Flask JWT callbacks
jwt.token_in_blocklist_loader(check_if_token_revoked)
jwt.user_identity_loader(user_identity_lookup)
jwt.user_lookup_loader(user_lookup_callback)

from .logging import *
from .mediarequest import *
from .oauths import *
from .scheduler import *

if __name__ == "__main__":
    socketio.run(app)
