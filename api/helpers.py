from flask import make_response
from peewee import IntegrityError
from pydantic import ValidationError

from app.exceptions import InvalidNotificationAgent


def try_catch(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return make_response({ "error": e.errors() }, 400)
        except IntegrityError as e:
            return make_response({ "error": str(e) }, 409)
        except InvalidNotificationAgent as e:
            return make_response({ "error": str(e) }, 422)
        except Exception as e:
            return make_response({ "error": str(e) }, 500)
        
    return wrapper