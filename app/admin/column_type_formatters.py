from datetime import datetime
from zoneinfo import ZoneInfo

def datetime_format(value: datetime):
    if not value:
        return ""
    return value.astimezone(
        ZoneInfo("Europe/Moscow")
    ).strftime("%d.%m.%Y %H:%M")