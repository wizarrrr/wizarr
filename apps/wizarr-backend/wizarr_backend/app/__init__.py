from dotenv import load_dotenv
from flask import Flask

from api import *

from .config import create_config
from .extensions import *
from .models.database import *
from .security import *
from .utils.clear_logs import clear_logs
from .migrator import run_migrations

# Get the base directory
BASE_DIR = path.abspath(path.dirname(__file__))

# Load environment variables
load_dotenv()

# Run migrations
run_migrations()

# Create the app
app = Flask(__name__)

app.config.update(**create_config(app))
schedule.authenticate(lambda auth: auth is not None)

# Initialize App Extensions
sess.init_app(app)
jwt.init_app(app)
cache.init_app(app)
api.init_app(app)
schedule.init_app(app)
socketio.init_app(app, async_mode="gevent" if app.config["GUNICORN"] else "threading", cors_allowed_origins="*", async_handlers=True)
# oauth.init_app(app)

# Clear cache on startup
with app.app_context():
    cache.clear()
    clear_logs()

# Register Flask JWT callbacks
jwt.token_in_blocklist_loader(check_if_token_revoked)
jwt.user_identity_loader(user_identity_lookup)
jwt.user_lookup_loader(user_lookup_callback)

from .logging import *
from .scheduler import *

if __name__ == "__main__":
    socketio.run(app)
