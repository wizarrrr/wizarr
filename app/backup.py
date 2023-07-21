# import base64
# import binascii
# import json
# import os
# from datetime import datetime

# from Crypto import Random
# from Crypto.Cipher import AES
# from Crypto.Protocol.KDF import PBKDF2
# from cryptography.fernet import Fernet
# from cryptography.hazmat.primitives import hashes
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# from flask import make_response, request
# from playhouse.shortcuts import model_to_dict

# from app import app
# from models import all_models


# class DateTimeEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, datetime):
#             return obj.isoformat()
#         return super().default(obj)
    
# class DateTimeDecoder(json.JSONDecoder):
#     def __init__(self, *args, **kwargs):
#         super().__init__(object_hook=self.object_hook, *args, **kwargs)
        
#     def object_hook(self, obj):
#         for key, value in obj.items():
#             if isinstance(value, str):
#                 try:
#                     obj[key] = datetime
#                 except ValueError:
#                     pass
#         return obj

# def generate_fernet_key(password, salt):
#     # Generate the Fernet key using PBKDF2HMAC
#     kdf = PBKDF2HMAC(
#         algorithm=hashes.SHA256(),
#         length=32,  # Fernet key size is 32 bytes
#         salt=salt,
#         iterations=100_000  # Adjust the number of iterations as per your requirements
#     )
#     key = kdf.derive(password.encode())

#     # Base64 encode the key
#     key_b64 = base64.urlsafe_b64encode(key)

#     # Return the Fernet key
#     return key_b64


# def encrypt_data(password, data):
#     # Generate a random salt
#     salt = os.urandom(16)

#     # Generate the Fernet key
#     fernet_key = generate_fernet_key(password, salt)

#     # Create a Fernet cipher object using the derived key
#     cipher = Fernet(fernet_key)

#     # Convert the data to JSON string
#     json_string = json.dumps(data, cls=DateTimeEncoder)

#     # Encrypt the JSON string using the Fernet cipher
#     encrypted_data = cipher.encrypt(json_string.encode())

#     # Return the encrypted data and salt
#     return encrypted_data, salt


# def decrypt_data(password, encrypted_data, salt):
#     # Generate the Fernet key
#     fernet_key = generate_fernet_key(password, salt)

#     # Create a Fernet cipher object using the derived key
#     cipher = Fernet(fernet_key)

#     # Decrypt the encrypted data
#     decrypted_data = cipher.decrypt(encrypted_data)

#     # Convert the decrypted data from JSON string to a Python object
#     data = json.loads(decrypted_data, cls=DateTimeDecoder)

#     # Return the decrypted data
#     return data

# def create_backup():
#     # Create a dictionary to store the data from all models
#     data = {}
    
#     # Loop through all models and store the data in the dictionary
#     for model_class in all_models:
#         table_name = model_class._meta.table_name
#         records = model_class.select()
        
#         data[table_name] = [model_to_dict(record) for record in records]
        
#     return data

# @app.route('/backup')
# def backup():
#     response = make_response(create_backup(), 200)
#     response.headers["Content-Type"] = "application/json"
    
#     return response

# @app.route('/backup/encrypted')
# def backup_encrypted():
#     # Create a backup
#     backup = create_backup()
    
#     # Encrypt the backup    
#     encrypted_backup, salt = encrypt_data(password="overseerr", data=backup)
    
#     response = make_response(encrypted_backup, 200)
#     response.headers["Content-Type"] = "application/octet-stream"
#     response.headers["Content-Disposition"] = "attachment; filename=" + str(salt) + ".backup"
    
#     return response

# # Decrypt a backup
# @app.route('/backup/decrypt', methods=['POST'])
# def decrypt_backup():
#     # Get the encrypted backup file
#     encrypted_backup = request.files['backup']
    
#     # Get the salt from the filename
#     salt = encrypted_backup.filename.split(".")[0]
    
#     # Convert the salt from string to bytes
#     salt = salt.encode()
    
#     # Decrypt the backup
#     decrypted_backup = decrypt_data(password="overseerr", encrypted_data=encrypted_backup.read(), salt=salt)
    
#     response = make_response(decrypted_backup, 200)
#     response.headers["Content-Type"] = "application/json"
    
#     return response
