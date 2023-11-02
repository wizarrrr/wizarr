from datetime import datetime

from cryptography.fernet import InvalidToken
from flask import make_response, request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from json import loads
from app.security import is_setup_required

from app.utils.backup import backup_database, encrypt_backup, generate_key, decrypt_backup, restore_database, test_backup

api = Namespace("Backup", description="Backup related operations", path="/backup")

# @api.route("/test")
# @api.route("/test/", doc=False)
# class BackupTest(Resource):

#     def get(self):
#         return test_backup()

@api.route("/download")
@api.route("/download/", doc=False)
class BackupDownload(Resource):
    """Backup related operations"""

    method_decorators = [jwt_required()]

    @api.doc(security="jwt")
    def post(self):
        # Get the password from the request
        password = request.form.get("password", None)

        # If the password is None, return an error
        if password is None:
            raise ValueError("Password is required")

        try:
            # Backup the database
            backup_unencrypted = backup_database()
            backup_encrypted = encrypt_backup(backup_unencrypted, generate_key(password))
        except InvalidToken:
            return { "message": "Invalid password" }, 400

        if backup_encrypted is None:
            return { "message": "An unknown error occurred" }, 400

        # Make a response as a download file
        file_name = f"wizarr-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.backup"

        response = make_response(backup_encrypted)
        response.headers["Content-Disposition"] = f"attachment; filename={file_name}"
        response.headers["Content-Type"] = "application/octet-stream"

        # Return the response
        return response


@api.route("/restore")
@api.route("/restore/", doc=False)
class BackupUpload(Resource):
    """Backup related operations"""

    method_decorators = [] if is_setup_required() else [jwt_required()]

    @api.doc(security="jwt")
    def post(self):
        # Get the posted file and password
        backup_file = request.files["backup"]
        password = request.form.get("password", None)

        print(password)

        # Check if the file exists
        if not backup_file:
            raise FileNotFoundError("File not found")

        # If the password is None, return an error
        if password is None:
            raise ValueError("Password is required")

        try:
            # Decrypt the backup
            data = decrypt_backup(backup_file.read(), generate_key(password))
        except InvalidToken:
            return { "message": "Invalid password" }, 400

        # Restore the backup
        if data is None or not restore_database(data):
            return { "message": "An unknown error occurred" }, 400

        # Return the response
        return { "message": "Backup restored successfully" }


@api.route("/decrypt")
@api.route("/decrypt/", doc=False)
class BackupDecrypt(Resource):
    """Backup related operations"""

    method_decorators = [jwt_required()]

    @api.doc(security="jwt")
    def post(self):
        # Get the posted file and password
        backup_file = request.files["backup"]
        password = request.form.get("password", None)

        # Check if the file exists
        if not backup_file:
            raise FileNotFoundError("File not found")

        # If the password is None, return an error
        if password is None:
            raise ValueError("Password is required")

        try:
            backup_decrypted = decrypt_backup(backup_file.read(), generate_key(password))
        except InvalidToken:
            return { "error": "Invalid password" }, 400

        if backup_decrypted is None:
            return { "error": "An unknown error occurred" }

        # Create file name based on input file name
        file_name = backup_file.filename.replace(".backup", ".json")

        response = make_response(backup_decrypted)
        response.headers["Content-Disposition"] = f"attachment; filename={file_name}"
        response.headers["Content-Type"] = "application/json"

        # Return the response
        return response


@api.route("/encrypt")
@api.route("/encrypt/", doc=False)
class BackupEncrypt(Resource):
    """Backup related operations"""

    method_decorators = [jwt_required()]

    @api.doc(security="jwt")
    def post(self):
        # Get the posted file and password
        backup_file = request.files["backup"]
        password = request.form.get("password", None)

        # Check if the file exists
        if not backup_file:
            raise FileNotFoundError("File not found")

        # If the password is None, return an error
        if password is None:
            raise ValueError("Password is required")

        # Encrypt the backup
        backup_decrypted = loads(backup_file.read())
        backup_encrypted = encrypt_backup(backup_decrypted, generate_key(password))

        if backup_encrypted is None:
            return { "error": "An unknown error occurred" }

        # Create file name based on input file name
        file_name = backup_file.filename.replace(".json", ".backup")

        response = make_response(backup_encrypted)
        response.headers["Content-Disposition"] = f"attachment; filename={file_name}"
        response.headers["Content-Type"] = "application/octet-stream"

        # Return the response
        return response
