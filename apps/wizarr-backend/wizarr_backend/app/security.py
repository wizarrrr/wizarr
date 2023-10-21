from os import mkdir, path
from secrets import token_hex
from flask import request
from flask_jwt_extended import verify_jwt_in_request
from playhouse.shortcuts import model_to_dict
from app.models.database import Sessions, Settings, Accounts, APIKeys
from definitions import DATABASE_DIR

# Yh this code looks messy but it works so ill tidy it up later
secret_key_file = path.join(DATABASE_DIR, "secret.key")

# Class to handle authentication for the scheduler
class SchedulerAuth:
    def get_authorization(self):
        return verify_jwt_in_request()

    def get_authenticate_header(self):
        return request.cookies.get("access_token_cookie")

def server_verified():
    verified = Settings.get_or_none(Settings.key == "server_verified")
    if verified: return bool(verified.value)
    return bool(verified)

# Generate a secret key, and store it in root/database/secret.key if it doesn't exist, return the secret key
def secret_key(length: int = 32) -> str:

    # Check if the database directory exists
    if not path.exists(DATABASE_DIR):
        mkdir(DATABASE_DIR)

    # Check if the secret key file exists
    if not path.exists(secret_key_file):
        # Generate a secret key and write it to the secret key file
        with open(path.join(secret_key_file), "w", encoding="utf-8") as f:
            secret = token_hex(length)
            f.write(secret)
            return secret

    # Read the secret key from the secret key file
    with open(path.join(secret_key_file), "r", encoding="utf-8") as f:
        secret = f.read()

    return secret

# def refresh_expiring_jwts(response):
#     try:
#         jwt = get_jwt()
#         if datetime.timestamp(datetime.now(timezone.utc) + timedelta(minutes=30)) > jwt["exp"]:
#             access_token = create_access_token(identity=get_jwt_identity())
#             Sessions.update(session=get_jti(access_token), expires=datetime.utcnow() + timedelta(days=1)).where(Sessions.session == jwt["jti"]).execute()
#             set_access_cookies(response, access_token)
#             info(f"Refreshed JWT for {get_jwt_identity()}")
#         return response
#     except (RuntimeError, KeyError):
#         return response


def check_if_token_revoked(_, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    session = Sessions.get_or_none((Sessions.access_jti == jti) | (Sessions.refresh_jti == jti))
    api = not APIKeys.select().where(APIKeys.jti == jti).exists()
    return session.revoked if session else api

def user_identity_lookup(user):
    return user

def user_lookup_callback(_, jwt_data):
    identity = jwt_data["sub"]
    try:
        user = Accounts.get_by_id(identity)
        return model_to_dict(user, recurse=True, backrefs=True, exclude=[Accounts.password])
    except Exception:
        return None

def is_setup_required():
    return not server_verified()
