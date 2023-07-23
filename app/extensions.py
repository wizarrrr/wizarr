from flask_session import Session
from flask_htmx import HTMX
from flask_babel import Babel
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from flask_restx import Api

from helpers.babel_locale import get_locale

sess = Session()
htmx = HTMX()
babel = Babel(locale_selector=get_locale)
jwt = JWTManager()
cache = Cache(config={"CACHE_TYPE": "simple"})
api = Api()
