# A Utility for Loading Configuration Files using Jinja2
def load_config(config_file: str, load_json: bool = True, **kwargs) -> dict[any, any] | str:
    """
    Load a configuration file using Jinja2.

    :param config_file: The path to the configuration file.
    :param load_json: Whether or not to load the configuration file as JSON.
    :param kwargs: Additional keyword arguments to pass to the Jinja2 environment.

    :return: The configuration file as a dictionary or string.
    """

    # Load app and json modules
    from app import app
    from json import loads

    # Load the configuration file
    data = app.jinja_env.get_template(config_file).render(**kwargs)

    # Load the configuration file as JSON
    if load_json: data = loads(data)

    # Return the configuration file
    return data
