from datetime import datetime, timedelta, timezone


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