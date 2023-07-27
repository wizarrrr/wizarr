from models.database import Settings


def get_settings(settings: list[str] = None, defaults: str = None):
    # Create the response and query variables
    response = {}
    query = None

    # Get all settings from the database if settings is None
    if settings is None:
        # Get all settings from the database
        query = Settings.select()
    else:
        # Get the settings from the database
        query = Settings.select().where(Settings.key.in_(settings))

    # If settings and defaults are not None, fill the response with the default values
    if settings is not None and defaults is not None:
        # Get the settings that are not in the database
        missing = [setting for setting in settings if setting not in query]

        # Fill the response with the default values
        response = {**{setting: defaults[setting] for setting in missing}, **response}

    # Return all settings
    return {**response, **{setting.key: setting.value for setting in query}}

def get_setting(setting: str, default: str = None):
    # Get the setting from the database
    setting = Settings.get_or_none(Settings.key == setting)

    # Return the value if the setting exists, otherwise return the default value
    return setting.value if setting else default

def create_settings(settings: dict[str, str], allowed_settings: list[str] = None):
    # Validate settings
    if allowed_settings and not all(key in allowed_settings for key in settings.keys()):
        raise ValueError("Invalid setting")

    [Settings.get_or_create(key=key, value=value) for key, value in settings.items()]

    # Return all settings for the keys that were created
    response = get_settings([key for key in settings.keys()])

    return response

def update_settings(settings: dict[str, str], allowed_settings: list[str] = None):
    # Validate settings
    if allowed_settings and not all(key in allowed_settings for key in settings.keys()):
        raise ValueError("Invalid setting")

    # Update the settings
    [Settings.update(value=value).where(Settings.key == key).execute() for key, value in settings.items()]

    # Return all settings for the keys that were updated
    response = get_settings([key for key in settings.keys()])

    return response

def update_setting(setting: str, value: str):
    # Update the setting
    Settings.update(value=value).where(Settings.key == setting).execute()

    # Return the setting
    return get_setting(setting)
