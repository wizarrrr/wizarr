from playhouse.shortcuts import model_to_dict
from schematics.exceptions import DataError

from models.database.accounts import Accounts
from models.wizarr.accounts import AccountsModel

# INDEX OF FUNCTIONS
# - Get Admins
# - Get Admin by ID
# - Get Admin by Username
# - Create Admin User
# - Update Admin User
# - Delete Admin User


# ANCHOR - Get Admins
def get_admins(password: bool = True) -> list[Accounts]:
    """Get all admins from the database
    :param password: Whether or not to include the password in the response
    :type password: bool

    :return: A list of admins
    """

    # Get all admins from the database
    admins: list[Accounts] = Accounts.select()
    exclude = []

    # Remove the password from the admin if password is False
    if password is False:
        exclude.append("password")

    # Convert the admins to a list of dictionaries
    admins = [AccountsModel(model_to_dict(admin, exclude=exclude)).to_primitive() for admin in admins]

    # Return a list of dicts
    return admins


# ANCHOR - Get Admin by ID
def get_admin_by_id(admin_id: int, verify: bool = True, password: bool = False) -> Accounts or None:
    """Get an admin by id
    :param id: The id of the admin
    :type id: int

    :param verify: Whether or not to verify the admin exists
    :type verify: bool

    :return: An admin
    """

    # Get the admin by id
    admin = Accounts.get_or_none(Accounts.id == admin_id)
    exclude = []

    # Check if the admin exists
    if admin is None and verify:
        raise ValueError("Admin does not exist")

    # Remove the password from the admin if password is False
    if password is False:
        exclude.append("password")

    # Return the admin
    return AccountsModel(model_to_dict(admin, exclude=exclude)).to_primitive()


# ANCHOR - Get Admin by Username
def get_admin_by_username(username: str, verify: bool = True, password: bool = False) -> Accounts or None:
    """Get an admin by username
    :param username: The username of the admin
    :type username: str

    :param verify: Whether or not to verify the admin exists
    :type verify: bool

    :return: An admin or None
    """

    # Get the admin by username
    admin = Accounts.get_or_none(Accounts.username == username)
    exclude = []

    # Check if the admin exists
    if admin is None and verify:
        raise ValueError("Admin does not exist")

    # Remove the password from the admin if password is False
    if password is False:
        exclude.append("password")

    # Return the admin
    return AccountsModel(model_to_dict(admin, exclude=exclude)).to_primitive()


# ANCHOR - Create Admin User
def create_admin_user(**kwargs) -> Accounts:
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

    # Create the admin user
    admin = AccountsModel(kwargs)

    # Validate the admin user
    admin.validate()

    # Validate username and email do not exist
    admin.check_username_exists()
    admin.check_email_exists()

    # Hash the password
    admin.hash_password()

    # Create the admin in the database
    new_admin: Accounts = Accounts.create(
        username=admin.username,
        password=admin.hashed_password,
        email=admin.email
    )

    # Return the user
    return get_admin_by_id(new_admin.id, password=False)


# ANCHOR - Update Admin User
def update_admin_user(admin_id: int, **kwargs) -> Accounts:
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
    db_admin = get_admin_by_id(admin_id, verify=False, password=True)

    # Check if the admin exists
    if db_admin is None:
        raise DataError({"admin_id": ["Admin does not exist"]})

    # Create the admin user
    admin = AccountsModel(kwargs)

    # Update the admin in the database
    admin.update_admin(db_admin)

    # Return the admin
    return admin.to_primitive()


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
