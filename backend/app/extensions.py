from flask_session import Session
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from flask_restx import Api
from flask_apscheduler import APScheduler
from flask_socketio import SocketIO

from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

sess = Session()
jwt = JWTManager()
cache = Cache()
api = Api()
schedule = APScheduler(scheduler=BackgroundScheduler(timezone=utc))
socketio = SocketIO(log_output=False)
