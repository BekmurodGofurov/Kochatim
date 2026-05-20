from datetime import datetime, timezone, timedelta


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_plus_seconds(seconds: int) -> datetime:
    return utcnow() + timedelta(seconds=int(seconds))


def utc_in_seconds(seconds: int):
    return utcnow() + timedelta(seconds=seconds)


def naive_utc(dt):
    # DB TIMESTAMP (timezone'siz) uchun
    return dt.astimezone(timezone.utc).replace(tzinfo=None)