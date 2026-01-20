# backend/utils/time.py
from datetime import datetime, timezone, timedelta


def utcnow():
    return datetime.now(timezone.utc)


def utc_in_seconds(seconds: int):
    return utcnow() + timedelta(seconds=seconds)


def naive_utc(dt):
    # DB TIMESTAMP (timezone'siz) uchun
    return dt.astimezone(timezone.utc).replace(tzinfo=None)