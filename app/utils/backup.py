from app.models.database.base import db
from app import app
from cryptography.fernet import Fernet, InvalidToken
from base64 import urlsafe_b64encode
from flask import request, make_response
from datetime import datetime
from json import dumps, loads

def backup_database():

    # Backup dictionary
    backup = {}

    # Get all tables
    db_tables = db.get_tables()

    # Get all rows in the table
    for table in db_tables:

        # Add the table to the backup dictionary
        backup[table] = []

        # Get all rows in the table
        db_rows = db.execute_sql(f"SELECT * FROM {table}")

        # Get all columns in the table
        db_columns = [column[0] for column in db_rows.description]

        # Add all rows to the backup dictionary
        for row in db_rows:
            backup[table].append(dict(zip(db_columns, row)))

    return backup

def generate_key(text):
    # Convert the text to bytes
    text = text.encode()

    # Pad the text to 32 bytes
    text = text + b"=" * (32 - len(text) % 32)

    # Encode the text to base64
    text = urlsafe_b64encode(text).decode()

    # Return the base64 encoded text
    return text

def encrypt_backup(backup: dict, key: str):
    # Create the encryption key
    key = Fernet(key)

    def encrypt_string(string: str):
        return key.encrypt(string.encode()).decode()

    backup_string = dumps(backup)
    encrypted_backup = encrypt_string(backup_string)

    return encrypted_backup




def decrypt_backup(backup: str, key: str):
    # Create the encryption key
    key = Fernet(key)

    def decrypt_string(string: str):
        return key.decrypt(string).decode()

    backup_string = decrypt_string(backup)

    return loads(backup_string)


@app.post("/backup/download")
def backup_route():

    # Get the password from the form
    password = request.form.get("password", None)

    # If the password is None, return an error
    if password is None:
        raise ValueError("Password is required")

    # Generate the key
    key = generate_key(password)

    # Encrypt the backup
    data = None

    try:
        data = encrypt_backup(backup_database(), key)
    except InvalidToken:
        return { "error": "Invalid password" }
    except Exception as e:
        return { "error": str(e) }

    if data is None:
        return { "error": "An unknown error occurred" }

    # Make a response as a download file
    file_name = f"wizarr-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.backup"

    response = make_response(data)
    response.headers["Content-Disposition"] = f"attachment; filename={file_name}"

    # Return the response
    return response


@app.post("/backup/restore")
def decrypt_route():

    # Get the posted file and password
    backup_file = request.files["backup"]
    password = request.form.get("password", None)

    # Check if the file exists
    if not backup_file:
        raise FileNotFoundError("File not found")

    # If the password is None, return an error
    if password is None:
        raise ValueError("Password is required")

    # Decrypt the backup
    data = None

    try:
        data = decrypt_backup(backup_file.read(), generate_key(password))
    except InvalidToken:
        return { "error": "Invalid password" }
    except Exception as e:
        return { "error": str(e) }

    if data is None:
        return { "error": "An unknown error occurred" }

    # Restore the backup
    return data



@app.route("/test/<string:subpath>")
def test_route(subpath):
    return generate_key(subpath)
