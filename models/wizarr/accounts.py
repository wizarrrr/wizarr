from os import getenv

from password_strength import PasswordPolicy
from playhouse.shortcuts import model_to_dict
from schematics.exceptions import DataError, ValidationError
from schematics.models import Model
from schematics.types import DateTimeType, EmailType, StringType
from werkzeug.security import generate_password_hash

from models.database.accounts import Accounts

min_password_length = int(getenv("MIN_PASSWORD_LENGTH", "8"))
min_password_uppercase = int(getenv("MIN_PASSWORD_UPPERCASE", "1"))
min_password_numbers = int(getenv("MIN_PASSWORD_NUMBERS", "1"))
min_password_special = int(getenv("MIN_PASSWORD_SPECIAL", "0"))

class AccountsModel(Model):
    """Admin User Model"""

    # ANCHOR - Admin User Model
    id = StringType(required=False)
    username = StringType(required=True)
    email = EmailType(required=False)
    password = StringType(required=True)
    confirm_password = StringType(required=False)
    hashed_password = StringType(required=False)
    last_login = DateTimeType(required=False, convert_tz=True)
    created = DateTimeType(required=False, convert_tz=True)


    # ANCHOR - Validate Password
    def validate_password(self, _, value):
        # Create password policy based on environment variables or defaults
        policy = PasswordPolicy.from_names(length=min_password_length, uppercase=min_password_uppercase, numbers=min_password_numbers, special=min_password_special)

        # Check if the password is strong enough
        if len(policy.test(value)) > 0:
            raise ValidationError("Password is not strong enough")


    # ANCHOR - Validate Confirm Password
    def validate_confirm_password(self, values, value):
        if value and value != values["password"]:
            raise ValidationError("Passwords do not match")


    # ANCHOR - Validate Username
    def check_username_exists(self, admin_id: int = None):
        if admin_id and Accounts.get_or_none(Accounts.username == self.username, Accounts.id != admin_id) is not None:
            raise DataError({"username": ["User with username already exists"]})
        elif not admin_id and Accounts.get_or_none(Accounts.username == self.username) is not None:
            raise DataError({"username": ["Username is already taken"]})


    # ANCHOR - Validate Email
    def check_email_exists(self, admin_id: int = None):
        if admin_id and Accounts.get_or_none(Accounts.email == self.email, Accounts.id != admin_id) is not None:
            raise DataError({"email": ["User with email already exists"]})
        elif not admin_id and Accounts.get_or_none(Accounts.email == self.email) is not None:
            raise DataError({"email": ["Email is already taken"]})


    # ANCHOR - Hash Password
    def hash_password(self):
        self.hashed_password = generate_password_hash(self.password, method="scrypt")
        return self.hashed_password


    # ANCHOR - Update Admin
    def update_admin(self, admin: Accounts):
        # Check if the admin exists
        if admin is None:
            raise DataError({"admin_id": ["Admin does not exist"]})

        # If password exists, check if confirm_password exists and if they match
        if self.password:
            if self.confirm_password and self.password != self.confirm_password:
                raise DataError({"confirm_password": ["Passwords do not match"]})

            # Hash the password and set it to the admin
            self.hash_password()
            setattr(admin, "password", self.hashed_password)

        # Check if username and email exist
        if self.username:
            self.check_username_exists(admin.id)

        if self.email:
            self.check_email_exists(admin.id)

        # Set the attributes of the model to the admin
        for key, value in self.to_primitive().items():
            if value is not None:
                setattr(admin, key, value)

        # Save the admin
        admin.save()

        # Set the attributes of the updated admin to the model
        for key, value in model_to_dict(admin).items():
            setattr(self, key, value)
