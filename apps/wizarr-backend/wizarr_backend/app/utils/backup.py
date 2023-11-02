from app.models.database.base import db, db_file
from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode
from json import dumps, loads
from datetime import datetime
from os import system, path
from definitions import DATABASE_DIR


def test_backup():

    db_tables = db.get_tables()
    backup = {}

    for table in db_tables:
        backup[table] = []
        db_rows = db.execute_sql(f"SELECT * FROM {table}")
        db_columns = [column[0] for column in db_rows.description]
        for row in db_rows:
            backup[table].append(dict(zip(db_columns, row)))

    return backup

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

    # Remove apscheduler_jobs table
    backup.pop("apscheduler_jobs", None)

    return backup


def restore_database(backup: dict):
    # Create a backup of the database file before restoring
    backup_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_location = path.join(DATABASE_DIR, "backups")
    system(f"cp {db_file} {path.join(backup_location, backup_filename)}")

    # Loop through all tables in the backup dictionary and restore them
    for table in backup:
        # Delete all rows in the table
        db.execute_sql(f"DELETE FROM {table}")

        # Loop through all rows in the table
        for row in backup[table]:
            # Get all columns in the table
            columns = list(row.keys())

            # Get all values in the table
            values = list(row.values())

            # Create the query
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})"

            # Execute the query
            db.execute_sql(query, values)

    return True


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
