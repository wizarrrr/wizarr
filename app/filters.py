from datetime import datetime
from os import getenv
from pendulum import parse
from app.utils.babel_locale import get_locale

def humanize(value):
    # Check if the value is a string
    if not isinstance(value, str):
        return "Unknown format"

    # If the value is a string, parse it
    value = parse(value)

    # Remove milliseconds
    value = value.replace(microsecond=0)
    timenow = datetime.utcnow().replace(microsecond=0)

    time_difference = value - timenow
    is_future = time_difference.total_seconds() > 0

    # Nearest human-readable time
    if abs(time_difference.days) > 364:
        years = abs(time_difference.days) // 364
        return f"{years} year{'s' if years > 1 else ''} {'from now' if is_future else 'ago'}"
    elif abs(time_difference.days) > 30:
        months = abs(time_difference.days) // 30
        return f"{months} month{'s' if months > 1 else ''} {'from now' if is_future else 'ago'}"
    elif abs(time_difference.days) > 7:
        weeks = abs(time_difference.days) // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} {'from now' if is_future else 'ago'}"
    elif abs(time_difference.days) > 1:
        days = abs(time_difference.days)
        return f"{days} day{'s' if days > 1 else ''} {'from now' if is_future else 'ago'}"
    elif abs(time_difference.total_seconds() / 3600) > 1:
        hours = abs(int(time_difference.total_seconds() / 3600))
        return f"{hours} hour{'s' if hours > 1 else ''} {'from now' if is_future else 'ago'}"
    elif abs(time_difference.total_seconds() / 60) > 1:
        minutes = abs(int(time_difference.total_seconds() / 60))
        return f"{minutes} minute{'s' if minutes > 1 else ''} {'from now' if is_future else 'ago'}"
    elif abs(time_difference.total_seconds()) > 1:
        seconds = abs(int(time_difference.total_seconds()))
        return f"{seconds} second{'s' if seconds > 1 else ''} {'from now' if is_future else 'ago'}"

    return "Unknown format"


def arrow_humanize(value):
    # Check if the value is a string
    if not isinstance(value, str):
        return "Unknown format"

    # Parse the datetime string
    parsed_datetime = parse(value)

    # Get the relative time difference from the current time
    try:
        relative_time = parsed_datetime.diff_for_humans(locale=get_locale())
    except ValueError:
        relative_time = parsed_datetime.diff_for_humans()

    return relative_time


def format_datetime(value):
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
    format_str = '%Y-%m-%d %H:%M:%S'
    parsed_date = datetime.strptime(str(value), format_str)
    return parsed_date.strftime(format)


def env(key, default=None):
    return getenv(key, default)

def split_string(value, delimiter, index=None):
    if index is None:
        return value.split(delimiter)
    else:
        return value.split(delimiter)[index]
