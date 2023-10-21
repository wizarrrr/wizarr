from playhouse.shortcuts import model_to_dict
from schematics.exceptions import DataError

from app.models.database.accounts import Accounts
from app.models.wizarr.accounts import AccountsModel

# INDEX OF FUNCTIONS
# - Get Accounts
# - Get Account by ID
# - Get Account by Username
# - Create Account User
# - Update Account User
# - Delete Account User


# ANCHOR - Get Accounts
def get_accounts(password: bool = True) -> list[Accounts]:
    """Get all accounts from the database
    :param password: Whether or not to include the password in the response
    :type password: bool

    :return: A list of accounts
    """

    # Get all accounts from the database
    accounts: list[Accounts] = Accounts.select()
    exclude = []

    # Remove the password from the account if password is False
    if password is False:
        exclude.append("password")

    # Convert the accounts to a list of dictionaries
    accounts = [AccountsModel(model_to_dict(account, exclude=exclude)).to_primitive() for account in accounts]

    # Return a list of dicts
    return accounts


# ANCHOR - Get Account by ID
def get_account_by_id(account_id: int, verify: bool = True, password: bool = False) -> Accounts or None:
    """Get an account by id
    :param id: The id of the account
    :type id: int

    :param verify: Whether or not to verify the account exists
    :type verify: bool

    :return: An account
    """

    # Get the account by id
    account = Accounts.get_or_none(Accounts.id == account_id)
    exclude = []

    # Remove the password from the account if password is False
    if password is False:
        exclude.append("password")

    # Return the account
    return AccountsModel(model_to_dict(account, exclude=exclude)).to_primitive()


# ANCHOR - Get Account by Username
def get_account_by_username(username: str, verify: bool = True, password: bool = False) -> Accounts or None:
    """Get an account by username
    :param username: The username of the account
    :type username: str

    :param verify: Whether or not to verify the account exists
    :type verify: bool

    :return: An account or None
    """

    # Get the account by username
    account = Accounts.get_or_none(Accounts.username == username)
    exclude = []

    # Check if the account exists
    if account is None and verify:
        raise ValueError("Account does not exist")

    # Remove the password from the account if password is False
    if password is False:
        exclude.append("password")

    # Return the account
    return AccountsModel(model_to_dict(account, exclude=exclude)).to_primitive()


# ANCHOR - Create Account User
def create_account(**kwargs) -> Accounts:
    """Create an account user
    :param username: The username of the account
    :type username: str

    :param email: The email of the account
    :type email: str

    :param password: The password of the account
    :type password: str

    :param confirm_password: The password of the account
    :type confirm_password: Optional[str]

    :return: An account
    """

    # Create the account user
    account = AccountsModel(kwargs)

    # Validate the account user
    account.validate()

    # Validate username and email do not exist
    account.check_username_exists()
    account.check_email_exists()

    # Hash the password
    account.hash_password()

    # Create the account in the database
    new_account: Accounts = Accounts.create(
        display_name=account.display_name,
        username=account.username,
        password=account.hashed_password,
        email=account.email,
        role=account.role
    )

    # Return the user
    return get_account_by_id(new_account.id, password=False)


# ANCHOR - Update Account User
def update_account(account_id: int, **kwargs) -> Accounts:
    """Update an account user
    :param id: The id of the account
    :type id: int

    :param kwargs: The attributes of the account
    :type kwargs: dict

    :return: An account
    """

    # Get the account by id
    account = Accounts.get_or_none(Accounts.id == account_id)

    # Update the account
    account = AccountsModel(kwargs).update_account(account)

    # Return the account
    return account.to_primitive()


# ANCHOR - Delete Account User
def delete_account(account_id: int) -> None:
    """Delete an account user
    :param id: The id of the account
    :type id: int

    :return: An account
    """

    # Get the account by id
    account = Accounts.get_or_none(Accounts.id == account_id)

    # Delete the account
    account.delete_instance()
