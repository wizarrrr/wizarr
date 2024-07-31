from app.models.database.users import Users
from app.models.users import UsersModel
from playhouse.shortcuts import model_to_dict
from datetime import datetime, timezone

# ANCHOR - Get Users
def get_users(as_dict: bool = True) -> list[Users]:
    """Get all users from the database
    :param dict: Whether or not to return as list of dicts

    :return: A list of users
    """

    # Get all users from the database
    users: list[Users] = Users.select()

    # Convert to a list of dicts
    if as_dict:
        users = [model_to_dict(user) for user in users]

    # Return all users
    return users


# ANCHOR - Get User by ID
def get_user_by_id(user_id: int, verify: bool = True) -> Users or None:
    """Get a user by id
    :param user_id: The id of the user
    :type user_id: int

    :param verify: Whether or not to verify the user exists
    :type verify: bool

    :return: A user
    """

    # Get the user by id
    user = Users.get_or_none(Users.id == user_id)

    # Check if the user exists
    if user is None and verify:
        raise ValueError("User does not exist")

    # Return the user
    return user


# ANCHOR - Get User by Username
def get_user_by_username(username: str, verify: bool = True) -> Users or None:
    """Get a user by username

    :param username: The username of the user
    :type username: str

    :param verify: Whether or not to verify the user exists
    :type verify: bool

    :return: A user
    """

    # Get the user by username
    user = Users.get_or_none(Users.username == username)

    # Check if the user exists
    if user is None and verify:
        raise ValueError("User does not exist")

    # Return the user
    return user


# ANCHOR - Get User by Email
def get_user_by_email(email: str, verify: bool = True) -> Users or None:
    """Get a user by email

    :param email: The email of the user
    :type email: str

    :param verify: Whether or not to verify the user exists
    :type verify: bool

    :return: A user
    """

    # Get the user by email
    user = Users.get_or_none(Users.email == email)

    # Check if the user exists
    if user is None and verify:
        raise ValueError("User does not exist")

    # Return the user
    return user

# ANCHOR - Get User by Token
def get_user_by_token(token: str, verify: bool = True) -> Users or None:
    """Get a user by token

    :param token: The token of the user
    :type token: str

    :param verify: Whether or not to verify the user exists
    :type verify: bool

    :return: A user
    """

    # Get the user by token
    user = Users.get_or_none(Users.token == token)

    # Check if the user exists
    if user is None and verify:
        raise ValueError("User does not exist")

    # Return the user
    return user


# ANCHOR - Get Users by Expiring
def get_users_by_expiring() -> list[Users]:
    """Get all users by expiring

    :return: A list of users
    """

    # Get all users by expiring
    users: list[Users] = Users.select().where(Users.expires <= datetime.now(timezone.utc))

    return users


# ANCHOR - Create User
def create_user(**kwargs) -> Users:
    """Create a user

    :param token: The token of the user
    :type token: str

    :param username: The username of the user
    :type username: str

    :param email: The email of the user
    :type email: str

    :param code: The code of the user
    :type code: str

    :param expires: The expiration date of the user
    :type expires: datetime

    :return: A user
    """

    # Validate user input
    form = UsersModel(**kwargs)
    user_model = form.model_dump()

    # If user already exists raise error (maybe change this to update user)
    if get_user_by_username(form.username, verify=False) is not None:
        user: Users = Users.update(**user_model).where(Users.username == form.username)
    else:
        user: Users = Users.create(**user_model)

    # Return the user
    return user

def edit_user_expiration(user_id: int, expiry: datetime) -> Users:
    """Add a user expiration date to an existing user or edit existing expiration date"""
    user = Users.get_by_id(user_id)
    user.expires = expiry
    user.save()
    return user

    