from sys import argv, exit as sys_exit
from time import sleep
from termcolor import colored
from tabulate import tabulate
from werkzeug.security import generate_password_hash
from threading import Thread

spinner_running = True

# Please wait message with spinner
def please_wait():
    print(colored("Please wait", "yellow"), end="")
    i = 0
    while spinner_running:
        print(colored(".", "yellow"), end="", flush=True)
        sleep(0.5)
        i += 1
        if i == 3:
            print("\b\b\b   \b\b\b", end="", flush=True)
            i = 0

def start_spinner():
    global spinner_running
    spinner_running = True
    Thread(target=please_wait).start()

def message(msg: str, color: str = "white"):
    global spinner_running
    spinner_running = False
    print("\r" + " " * 30 + "\r", end="", flush=True)
    print(colored(msg, color), flush=True)


# Declared functions
def help_message():
    # Usage message
    print(colored("Usage: python manage.py <command> [args]", "green"))
    print()

    # Print table of commands, args, and descriptions
    print(tabulate([[command, " ".join([f"--{arg_name} " for arg_name in args["args"]]) if "args" in args else "", args["description"]] for command, args in VALID_COMMANDS.items()], headers=["Command", "Args", "Description"]))

    print()
    sys_exit(0)



def reset_password(username: str, password: str):
    # Start the spinner
    start_spinner()

    # Import the Accounts model
    from app.models.database.accounts import Accounts

    # Get the user
    user = Accounts.get_or_none(username=username)

    # Check if the user exists
    if not user:
        message(f"User `{username}` does not exist", "red")
        sys_exit(1)

    # Set the new password
    user.password = generate_password_hash(password, method="scrypt")

    # Save the user
    user.save()

    # Print the user
    message(f"Successfully reset password for user `{username}`", "green")
    sys_exit(0)



def create_user(username: str, password: str, email: str):
    # Start the spinner
    start_spinner()

    # Import the Accounts model
    from app.models.database.accounts import Accounts

    # Check if the user exists
    if Accounts.get_or_none(username=username):
        message(f"User `{username}` already exists", "red")
        sys_exit(1)

    # Check if the email is valid and not already in use
    if email:
        if not "@" in email:
            message(f"Email `{email}` is not valid", "red")
            sys_exit(1)
        if Accounts.get_or_none(email=email):
            message(f"Email `{email}` is already in use", "red")
            sys_exit(1)

    # Create the user
    user = Accounts.create(
        username=username,
        password=generate_password_hash(password, method="scrypt"),
        email=email,
        role="admin"
    )

    # Print the user
    message(f"Successfully created user `{user.username}`", "green")


def check_user(username: str):
    # Start the spinner
    start_spinner()

    # Import the Accounts model
    from app.models.database.accounts import Accounts

    # Get the user
    user = Accounts.get_or_none(username=username)

    # Check if the user exists
    if not user:
        message(f"User `{username}` does not exist", "red")
        sys_exit(1)

    # Print the user
    message(f"User `{user.username}` exists", "green")
    sys_exit(0)


def delete_user(username: str, y: bool = False):
    # Ask for confirmation
    if not y:
        if input(colored(f"Are you sure you want to delete user `{username}`? (y/n) ", "yellow")).lower() != "y":
            sys_exit(1)

    # Start the spinner
    start_spinner()

    # Import the Accounts model
    from app.models.database.accounts import Accounts

    # Get the user
    user = Accounts.get_or_none(username=username)

    # Check if the user exists
    if not user:
        message(f"User `{username}` does not exist", "red")
        sys_exit(1)

    # Delete the user
    user.delete_instance()

    # Print the user
    message(f"Successfully deleted user `{username}`", "green")
    sys_exit(0)


# Declared variables
VALID_COMMANDS = {
    "--help": {
        "description": "Shows this help message",
        "function": help_message,
    },
    "reset_password": {
        "description": "Resets the password of the specified user",
        "args": {
            "username": {
                "description": "The username of the user to reset the password of",
                "required": True,
            },
            "password": {
                "description": "The new password of the user",
                "required": True,
            },
        },
        "function": reset_password,
    },
    "create_user": {
        "description": "Creates a new user",
        "args": {
            "username": {
                "description": "The username of the user to create",
                "required": True,
            },
            "password": {
                "description": "The password of the user to create",
                "required": True,
            },
            "email": {
                "description": "The email of the user to create",
                "required": True,
            },
        },
        "function": create_user,
    },
    "delete_user": {
        "description": "Deletes the specified user",
        "args": {
            "username": {
                "description": "The username of the user to delete",
                "required": True,
            },
            "y": {
                "description": "Skips the confirmation prompt",
                "required": False,
            },
        },
        "function": delete_user,
    },
    "check_user": {
        "description": "Checks if the specified user exists",
        "args": {
            "username": {
                "description": "The username of the user to check",
                "required": True,
            },
        },
        "function": check_user,
    },
}

# Check if argv[1] exists
if len(argv) < 2:
    print(colored("Please specify a command like `python manage.py reset_password`", "red"))
    print("See `python manage.py --help` for a list of valid commands")
    sys_exit(1)


# Check if the command is valid
if argv[1] not in VALID_COMMANDS:
    print(colored(f"Invalid command `{argv[1]}`", "red"))
    print("See `python manage.py --help` for a list of valid commands")
    sys_exit(1)

# Check if the command has a function
if "function" not in VALID_COMMANDS[argv[1]]:
    print(colored(f"Command `{argv[1]}` does not have a function", "red"))
    sys_exit(1)


# Check if the command has args
if "args" in VALID_COMMANDS[argv[1]]:
    try:
        # if the last arg is --help after the command print the commands description and args descriptions
        if len(argv) == 3 and argv[2] == "--help":
            print(colored(f"{argv[1]} - {VALID_COMMANDS[argv[1]]['description']}", "green"))
            print()
            print(tabulate([[arg_name, arg["description"]] for arg_name, arg in VALID_COMMANDS[argv[1]]["args"].items()], headers=["Arg", "Description"]))
            print()
            sys_exit(0)

        # Convert args to key value pairs
        kwargs = {argv[i].replace("--", ""): argv[i + 1] for i in range(2, len(argv), 2)}

        # Check if the command has invalid args
        if any([arg_name not in VALID_COMMANDS[argv[1]]["args"] for arg_name in kwargs]):
            print(colored(f"Command `{argv[1]}` has invalid args", "red"))
            print(f"python manage.py {argv[1]}", " ".join([f"--{arg_name} <value>" for arg_name in VALID_COMMANDS[argv[1]]["args"]]))
            print()
            sys_exit(1)

        # Check that all required args are present
        if any([arg_name not in kwargs for arg_name, arg in VALID_COMMANDS[argv[1]]["args"].items() if arg["required"]]):
            print(colored(f"Command `{argv[1]}` is missing required args", "red"))
            print(f"python manage.py {argv[1]}", " ".join([f"--{arg_name} <value>" for arg_name, arg in VALID_COMMANDS[argv[1]]["args"].items() if arg["required"]]))
            print()
            sys_exit(1)

        # Run the command
        VALID_COMMANDS[argv[1]]["function"](**kwargs)

    except IndexError:
        print(colored(f"Command `{argv[1]}` requires args", "red"))
        print(f"python manage.py {argv[1]}", " ".join([f"--{arg_name} <value>" for arg_name in VALID_COMMANDS[argv[1]]["args"]]))
        print()
        sys_exit(1)

    except Exception as e:
        print(colored(f"Something went wrong while parsing args for command `{argv[1]}`", "red"))
        print(e)
        print()
        sys_exit(1)
else:
    try:
        # Run the command
        VALID_COMMANDS[argv[1]]["function"]()
    except Exception as e:
        print(colored(f"Something went wrong while running command `{argv[1]}`", "red"))
        print(e)
        print()
        sys_exit(1)


sys_exit(0)
