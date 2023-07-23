from models.admins import AdminsModel, Admins
from werkzeug.security import generate_password_hash
from peewee import IntegrityError
from playhouse.shortcuts import model_to_dict

# INDEX OF FUNCTIONS
# - Get Admins
# - Get Admin by ID
# - Get Admin by Username
# - Create Admin User
# - Update Admin User
# - Delete Admin User


# ANCHOR - Get Admins
def get_admins(password: bool = True) -> list[Admins]:
    """Get all admins from the database
    :param password: Whether or not to include the password in the response
    :type password: bool

    :return: A list of admins
    """

    # Get all admins as a list of dicts
    admins: list[Admins] = Admins.select()

    # Convert to a list of dicts
    admins = [model_to_dict(admin) for admin in admins]

    # Remove the password from each admin if password is False
    if password is False:
        admins = [
            {k: v for k, v in admin.items() if k != "password"} for admin in admins
        ]

    # Return a list of dicts
    return admins


# ANCHOR - Get Admin by ID
def get_admin_by_id(admin_id: int, verify: bool = True) -> Admins or None:
    """Get an admin by id
    :param id: The id of the admin
    :type id: int

    :param verify: Whether or not to verify the admin exists
    :type verify: bool

    :return: An admin
    """

    # Get the admin by id
    admin = Admins.get_or_none(Admins.id == admin_id)

    # Check if the admin exists
    if admin is None and verify:
        raise ValueError("Admin does not exist")

    # Return the admin
    return admin


# ANCHOR - Get Admin by Username
def get_admin_by_username(username: str, verify: bool = True) -> Admins or None:
    """Get an admin by username
    :param username: The username of the admin
    :type username: str

    :param verify: Whether or not to verify the admin exists
    :type verify: bool

    :return: An admin or None
    """

    # Get the admin by username
    admin = Admins.get_or_none(Admins.username == username)

    # Check if the admin exists
    if admin is None and verify:
        raise ValueError("Admin does not exist")

    # Return the admin
    return admin


# ANCHOR - Create Admin User
def create_admin_user(**kwargs) -> Admins:
    """Create an admin user
    :param username: The username of the admin
    :type username: str

    :param email: The email of the admin
    :type email: str

    :param password: The password of the admin
    :type password: str

    :param confirm_password: The password of the admin
    :type confirm_password: Optional[str]

    :return: An admin
    """

    # Validate user input
    form = AdminsModel(**kwargs)

    # Validate passwords match
    if kwargs.get("confirm_password", None) is not None:
        if str(form.password) != str(kwargs.get("confirm_password")):
            raise ValueError("Passwords do not match")

    # Validate username is not taken
    if get_admin_by_username(form.username, False) is not None:
        raise ValueError("Username is already taken")

    # Hash the password
    form.password = generate_password_hash(form.password, method="scrypt")

    # Extract the data from the model
    admin = form.model_dump(
        exclude_defaults=True, exclude_unset=True, exclude_none=True
    )

    # Create the admin in the database
    admin: Admins = Admins.create(**admin)

    # Return the user
    return admin


# ANCHOR - Update Admin User
def update_admin_user(admin_id: int, **kwargs) -> Admins:
    """Update an admin user
    :param id: The id of the admin
    :type id: int

    :param username: The username of the admin
    :type username: str

    :param email: The email of the admin
    :type email: str

    :param password: The password of the admin
    :type password: str

    :param confirm_password: The password of the admin
    :type confirm_password: Optional[str]

    :return: An admin
    """

    # Get the admin by id
    admin = get_admin_by_id(admin_id, False)

    # Check if the admin exists
    if admin is None:
        raise ValueError("Admin does not exist")

    # Validate user input
    form = AdminsModel(*kwargs)

    # Validate passwords match
    if kwargs.get("confirm_password", None) is not None:
        if str(form.password) != str(kwargs.get("confirm_password")):
            raise IntegrityError("Passwords do not match")

    # Hash the password
    if form.password:
        form.password = generate_password_hash(form.password, method="scrypt")

    # Extract the data from the model
    admin_data = form.model_dump(
        exclude_defaults=True, exclude_unset=True, exclude_none=True
    )

    # Update the admin
    admin.update(**admin_data)

    # Return the admin
    return admin


# ANCHOR - Delete Admin User
def delete_admin_user(admin_id: int) -> None:
    """Delete an admin user
    :param id: The id of the admin
    :type id: int

    :return: An admin
    """

    # Get the admin by id
    admin = get_admin_by_id(admin_id, False)

    # Check if the admin exists
    if admin is None:
        raise ValueError("Admin does not exist")

    # Delete the admin
    admin.delete_instance()