from app.models.database import Settings

def get_media_settings():
    # Get the media settings
    Settings.select().where(Settings.key.in_(["server_url", "server_api_key"]))

    # Return the media settings
    return {setting.key: setting.value for setting in Settings.select().where(Settings.key.in_(["server_url", "server_api_key"]))}


def get_settings(settings: list[str] = None, defaults: str = None, disallowed: list[str] = None):
    # Create the response and query variables
    response = {}

    # Create the query functions for the settings
    query_func = {
        "all": lambda: Settings.select(),
        "settings": lambda: Settings.select().where(Settings.key.in_(settings)),
        "disallowed": lambda: Settings.select().where(Settings.key.not_in(disallowed)) if disallowed is not None else None
    }

    # Perform the query based on the settings or disallowed
    query = query_func["all"] if settings is None and disallowed is None else query_func["settings"] if settings is not None else query_func["disallowed"]()

    # If settings and defaults are not None, fill the response with the default values
    if settings is not None and defaults is not None:
        missing = [setting for setting in settings if setting not in query]
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
