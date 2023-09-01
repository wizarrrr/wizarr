def arrow_humanize(value):
    from pendulum import parse, now
    from app.utils.babel_locale import get_locale

    # Check if the value is a string
    if not isinstance(value, str):
        return "Unknown format"

    # Parse the datetime string
    parsed_datetime = parse(value)
    utc_now = now("UTC")

    # Get the relative time difference from the current time
    try:
        relative_time = parsed_datetime.diff_for_humans(locale=get_locale())
    except Exception:
        relative_time = utc_now.diff_for_humans(other=parsed_datetime).replace("after", "ago")

    return relative_time


def format_datetime(value):
    from datetime import datetime

    format_str = '%Y-%m-%d %H:%M:%S.%f%z'
    def get_time_duration(target_date):
        now = datetime.now(target_date.tzinfo)
        duration = target_date - now
        duration_seconds = duration.total_seconds()

        hours = int(duration_seconds / 3600)
        minutes = int((duration_seconds % 3600) / 60)
        seconds = int(duration_seconds % 60)

        return hours, minutes, seconds

    parsed_date = datetime.strptime(value, format_str)
    hms = get_time_duration(parsed_date)

    if hms[0] > 0:
        return f"{hms[0]}h {hms[1]}m {hms[2]}s"
    elif hms[1] > 0:
        return f"{hms[1]}m {hms[2]}s"
    else:
        return f"{hms[2]}s"

def date_format(value, format="%Y-%m-%d %H:%M:%S"):
    from datetime import datetime

    format_str = '%Y-%m-%d %H:%M:%S'
    parsed_date = datetime.strptime(str(value), format_str)
    return parsed_date.strftime(format)


def env(key, default=None):
    from os import getenv

    return getenv(key, default)

def split_string(value, delimiter, index=None):
    if index is None:
        return value.split(delimiter)
    else:
        return value.split(delimiter)[index]
