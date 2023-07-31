from datetime import datetime
from os import getenv
from dateutil.parser import parse

def time_ago(value):
    # Check if the value is a string
    if not isinstance(value, str):
        return "Unknown format"

    # If the value is a string, parse it
    value = parse(value)

    # days ago if more than 1 day, else hours ago if more than 1 hour, else minutes ago if more than 1 minute, else seconds ago
    if (datetime.utcnow() - value).days > 0:
        return f"{(datetime.utcnow() - value).days} day{'s' if (datetime.utcnow() - value).days > 1 else ''} ago"
    elif (datetime.utcnow() - value).seconds / 3600 > 1:
        return f"{int((datetime.utcnow() - value).seconds / 3600)} hour{'s' if int((datetime.utcnow() - value).seconds / 3600) > 1 else ''} ago"
    elif (datetime.utcnow() - value).seconds / 60 > 1:
        return f"{int((datetime.utcnow() - value).seconds / 60)} min{'s' if int((datetime.utcnow() - value).seconds / 60) > 1 else ''} ago"
    else:
        return f"{(datetime.utcnow() - value).seconds} sec{'s' if (datetime.utcnow() - value).seconds > 1 else ''} ago"

def time_until(value):
    print(value)
    # Check if the value is a string
    if not isinstance(value, str):
        return "Unknown format"

    # If the value is a string, parse it
    value = parse(value)

    # days if more than 1 day, else hours if more than 1 hour, else minutes if more than 1 minute, else seconds
    if (value - datetime.utcnow()).days > 0:
        return f"{(value - datetime.utcnow()).days} day{'s' if (value - datetime.utcnow()).days > 1 else ''}"
    elif (value - datetime.utcnow()).seconds / 3600 > 1:
        return f"{int((value - datetime.utcnow()).seconds / 3600)} hour{'s' if int((value - datetime.utcnow()).seconds / 3600) > 1 else ''}"
    elif (value - datetime.utcnow()).seconds / 60 > 1:
        return f"{int((value - datetime.utcnow()).seconds / 60)} min{'s' if int((value - datetime.utcnow()).seconds / 60) > 1 else ''}"
    else:
        return f"{(value - datetime.utcnow()).seconds} sec{'s' if (value - datetime.utcnow()).seconds > 1 else ''}"


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
