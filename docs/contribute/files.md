## Files Guide
This outlines the structure of the files in the project and how each part of structure is utilized. This is a guide for developers who want to contribute to the project.

### File Structure
The file structure is as follows:

- `api/` - Contains each API endpoint, organized `api/<endpoint_path>_api.py`
- `helpers/` - Contains helper functions for the API, organized `helpers/<helper_name>.py`
- `models/` - Contains multiple folders based usage:
    - `database/` - Contains the database models, organized `models/database/<model_name>.py`
    - `api/` - Contains the mashalling models for the API, organized `models/api/<model_name>.py`
    - `wizarr/` - Contains the models used for schematics data validation, organized `models/wizarr/<model_name>.py`

- `tests/` - Contains frontend tests using cypress
- `docs/` - Contains the documentation for the project
- `migrations/` - Contains the database migration scripts
- `app/` - Contains multiple folders used for the main execution of the program
    - `templates/` - Contains the templates for the frontend
        - See more about the frontend in the [frontend guide](frontend.md)
    - `static/` - Contains the static files for the frontend




## Components

#### Table of Contents
<details><summary>Click to expand</summary>
- [Accounts](#accounts)
- [Authentication](#authentication)
</details>

### Accounts
Accounts are what admin users use to login to the system. They use JWT tokens to authenticate themselfs to the system. The accounts are stored in the database and are hashed. The following files all relate to account based operations:

- `api/accounts_api.py` - Contains the API endpoints for account based operations
    - `/accounts` - `GET` - Returns all accounts
    - `/accounts` - `POST` - Creates a new account
    - `/accounts/<account_id>` - `GET` - Returns a specific account
    - `/accounts/<account_id>` - `PUT` - Updates a specific account
    - `/accounts/<account_id>` - `DELETE` - Deletes a specific account

- `helpers/accounts.py` - Contains helper functions for account based operations
    - `get_accounts()` - Returns all accounts
    - `get_account_by_id()` - Returns a specific account by id
    - `get_account_by_username()` - Returns a specific account by username
    - `create_account()` - Creates a new account
    - `update_account()` - Updates a specific account
    - `delete_account()` - Deletes a specific account

- `models/database/account.py` - Contains the database model for accounts
- `models/api/account.py` - Contains the mashalling model for accounts

- `models/wizarr/account.py` - Contains the schematics model for accounts
    - `AccountsModel` - Class for validating account data
        - `validate()` - Validates the data provided to the class during initialization
        - `check_username_exists()` - Checks if the username provided already exists in the database
        - `check_email_exists()` - Checks if the email provided already exists in the database
        - `hash_password()` - Hashes the password provided
        - `update_account()` - Updates the account provided


### Authentication
Authentication is the process of verifying that a user under accounts is who they say they are. This is done by using JWT tokens. The following files all relate to authentication based operations:

- `api/authenticate_api.py` - Contains the API endpoints for authentication based operations
    - `/login` - `POST` - Logs in a user based on the username and password provided
    - `/logout` - `POST` - Logs out a user using JWT in cookies

- `helpers/authenticate.py` - Contains helper functions for authentication based operations
    - `login_to_account()` - Logs in a user
    - `logout_of_account()` - Logs out a user

- `models/api/authenticate.py` - Contains the mashalling model for authentication

- `models/wizarr/authenticate.py` - Contains the schematics model for authentication
    - `AuthenticateModel` - Class for validating authentication data
        - `get_token()` - Returns a JWT token for the user provided
        - `set_access_cookies()` - Sets the JWT token in cookies
        - `unset_access_cookies()` - Unsets the JWT token in cookies
        - `get_admin()` - Returns the admin user
        - `get_token_from_cookie()` - Returns the JWT token from cookies
        - `destroy_session()` - Destroys the session for the user

