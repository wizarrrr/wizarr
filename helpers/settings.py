from models import Settings


def get_settings(settings: list[str] = None):
    # Get all settings from the database if settings is None
    if settings is None:
        query = Settings.select()
    else:
        query = Settings.select().where(Settings.key.in_(settings))

    # Return all settings and notification agents
    return {setting.key: setting.value for setting in query}


def create_settings(settings: dict[str, str], allowed_settings: list[str] = None):
    # Validate settings
    if allowed_settings and not all(key in allowed_settings for key in settings.keys()):
        raise ValueError("Invalid setting")
    
    [Settings.get_or_create(key=key, value=value) for key, value in settings.items()]
    
    # Return all settings for the keys that were created
    response = get_settings([key for key in settings.keys()])
    
    return response