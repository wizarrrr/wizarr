from peewee import IntegrityError
from pydantic import ValidationError
from flask import make_response

def try_catch(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return make_response({ "error": e.errors() }, 400)
        except IntegrityError as e:
            return make_response({ "error": str(e) }, 409)
        except Exception as e:
            return make_response({ "error": str(e) }, 500)
    return wrapper