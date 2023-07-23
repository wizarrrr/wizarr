from flask import request


def convert_to_form():
    def wrapper(fn):
        def decorator(*args, **kwargs):
            if request.method in ["POST", "PUT", "PATCH"] and request.is_json:
                request.form = request.get_json()
            return fn(*args, **kwargs)

        return decorator

    return wrapper
