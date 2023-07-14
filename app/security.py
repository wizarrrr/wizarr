from functools import wraps
from os import getenv

from flask import make_response, redirect
from flask_jwt_extended import verify_jwt_in_request


# Generate a secret key, and store it in root/database/secret.key if it doesn't exist, return the secret key
def secret_key(length: int = 32) -> str:
    from os import mkdir, path
    from secrets import token_hex

    from app import base_dir

    # Check if the database directory exists
    if not path.exists("database"):
        mkdir("database")
        
    # Check if the secret key file exists
    if not path.exists(path.join(base_dir, "../", "database/secret.key")):
        # Generate a secret key and write it to the secret key file
        with open(path.join(base_dir, "../", "database/secret.key"), "w") as f:
            secret_key = token_hex(length)
            f.write(secret_key)
            return secret_key
    
    # Read the secret key from the secret key file
    with open(path.join(base_dir, "../", "database/secret.key"), "r") as f:
        secret_key = f.read()
        
    return secret_key


def login_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            if getenv("DISABLE_BUILTIN_AUTH", "false") == "false":
                try:
                    verify_jwt_in_request()
                except Exception as e:
                    return make_response(redirect("/login"))
            
            return fn(*args, **kwargs)

        return decorator

    return wrapper

def logged_out_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            if getenv("DISABLE_BUILTIN_AUTH", "false") == "true":
                return fn(*args, **kwargs)
            
            try:
                verify_jwt_in_request()
            except Exception as e:
                return fn(*args, **kwargs)
            
            return make_response(redirect("/"))

        return decorator

    return wrapper