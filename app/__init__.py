from os import getenv, environ

from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import verify_jwt_in_request, jwt_required
from jinja2 import ChoiceLoader, FileSystemLoader

from api import *
from migrations import migrate

from .config import create_config
from .extensions import *
from .filters import *
from .globals import create_globals
from .models.database import *
from .routes import page_not_found, routes
from .security import *
from .utils.babel_locale import get_locale
from .utils.check_enviroment import check_enviroment
from .utils.compile_swagger import compile_swagger

BASE_DIR = path.abspath(path.dirname(__file__))

# Load environment variables
load_dotenv()

# Create the app
app = Flask(__name__)

# Override Flask server name if it contains http or https
if getenv("APP_URL") and getenv("APP_URL", "").startswith("http://") or getenv("APP_URL", "").startswith("https://"):
    host = getenv("APP_URL").replace("http://", "").replace("https://", "")
    app.config["SERVER_NAME"] = host
    environ["APP_URL"] = host

# Define a custom template loader for the other_templates folder
views_loader = FileSystemLoader("app/views")
config_loader = FileSystemLoader("app/configs")
app.jinja_loader = ChoiceLoader([app.jinja_loader, views_loader, config_loader])

# Run database migrations scripts
if not app.debug or getenv("MIGRATE"):
    migrate()

app.config.update(**create_config(app))
app.jinja_env.globals.update(**create_globals(app))

schedule.authenticate(lambda auth: auth is not None)

# Initialize App Extensions
sess.init_app(app)
htmx.init_app(app)
jwt.init_app(app)
cache.init_app(app)
api.init_app(app)
schedule.init_app(app)
socketio.init_app(app, async_mode="gevent" if app.config["GUNICORN"] else "threading", cors_allowed_origins="*", async_handlers=True)
babel.init_app(app, locale_selector=get_locale)
oauth.init_app(app)

# Clear cache on startup
with app.app_context():
    cache.clear()
    compile_swagger(api)

# Register Jinja2 filters
app.add_template_filter(format_datetime)
app.add_template_filter(date_format)
app.add_template_filter(env, "getenv")
app.add_template_filter(humanize)
app.add_template_filter(arrow_humanize)
app.add_template_filter(split_string, "split")

# Register Flask blueprints
app.after_request(refresh_expiring_jwts)
app.before_request(check_enviroment)

# Register Flask JWT callbacks
jwt.token_in_blocklist_loader(check_if_token_revoked)
jwt.user_identity_loader(user_identity_lookup)
jwt.user_lookup_loader(user_lookup_callback)

# Register the routes
app.register_blueprint(routes)
app.register_error_handler(404, page_not_found)

from .logging import *
from .mediarequest import *
from .oauths import *
from .partials import *
from .scheduler import *
from .utils.backup import *

if __name__ == "__main__":
    socketio.run(app)
