from os import getenv

from password_strength import PasswordPolicy
from playhouse.shortcuts import model_to_dict
from schematics.exceptions import DataError, ValidationError
from schematics.models import Model
from schematics.types import DateTimeType, EmailType, StringType, BooleanType
from werkzeug.security import generate_password_hash, check_password_hash

from app.models.database.accounts import Accounts

min_password_length = int(getenv("MIN_PASSWORD_LENGTH", "8"))
min_password_uppercase = int(getenv("MIN_PASSWORD_UPPERCASE", "1"))
min_password_numbers = int(getenv("MIN_PASSWORD_NUMBERS", "1"))
min_password_special = int(getenv("MIN_PASSWORD_SPECIAL", "0"))

class AccountsModel(Model):
    """Account Account Model"""

    # ANCHOR - Account Account Model
    id = StringType(required=False)
    avatar = StringType(required=False)
    display_name = StringType(required=False, default="")
    username = StringType(required=True)
    email = EmailType(required=False)
    password = StringType(required=True)
    confirm_password = StringType(required=False)
    hashed_password = StringType(required=False)
    role = StringType(required=False, default="user")
    tutorial = BooleanType(default=False)
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


    # ANCHOR - Validate Role
    def validate_role(self, _, value):
        if value not in ["admin", "moderator", "user"]:
            raise ValidationError("Invalid role value")


    # ANCHOR - Validate Username
    def check_username_exists(self, account_id: int = None):
        if account_id and Accounts.get_or_none(Accounts.username == self.username, Accounts.id != account_id) is not None:
            raise DataError({"username": ["Account with that username already exists"]})
        elif not account_id and Accounts.get_or_none(Accounts.username == self.username) is not None:
            raise DataError({"username": ["Username is already taken"]})


    # ANCHOR - Validate Email
    def check_email_exists(self, account_id: int = None):
        if account_id and Accounts.get_or_none(Accounts.email == self.email, Accounts.id != account_id) is not None:
            raise DataError({"email": ["Account with that email already exists"]})
        elif not account_id and Accounts.get_or_none(Accounts.email == self.email) is not None:
            raise DataError({"email": ["Email is already taken"]})


    # ANCHOR - Hash Password
    def hash_password(self):
        self.hashed_password = generate_password_hash(self.password, method="scrypt")
        return self.hashed_password

    # ANCHOR - Update Account
    def update_account(self, account: Accounts):
        # Check if the account exists
        if account is None:
            raise DataError({"account_id": ["Account does not exist"]})

        # If password exists, check if confirm_password exists and if they match
        if self.password:
            if self.confirm_password and self.password != self.confirm_password:
                raise DataError({"confirm_password": ["Passwords do not match"]})

            # Hash the password and set it to the account
            self.hash_password()
            setattr(account, "password", self.hashed_password)

        # Check if username and email exist
        if self.username:
            self.check_username_exists(account.id)

        if self.email:
            self.check_email_exists(account.id)

        # Set the attributes of the model to the account
        for key, value in self.to_primitive().items():
            if value is not None:
                setattr(account, key, value)

        # Save the account
        account.save()

        # Set the attributes of the updated account to the model
        for key, value in model_to_dict(account).items():
            setattr(self, key, value)


    # ANCHOR - Chnage password for user
    def change_password(self):
        old_password  = self.form.get("old_password")
        new_password = self.form.get("new_password")
        username = self.form.get("username")
        # get account by username
        account = Accounts.get_or_none(Accounts.username == username)

        # Create password policy based on environment variables or defaults
        policy = PasswordPolicy.from_names(length=min_password_length, uppercase=min_password_uppercase, numbers=min_password_numbers, special=min_password_special)

        # Check if the password is strong enough
        if len(policy.test(new_password)) > 0:
            raise ValidationError("Password is not strong enough")

        # First, check if the old_password matches the account's current password
        if not check_password_hash(account.password, old_password):
            raise ValidationError("Old password does not match.")

        # Next update the password on account
        account.password = generate_password_hash(new_password, method="scrypt")
        account.save()
        return True

