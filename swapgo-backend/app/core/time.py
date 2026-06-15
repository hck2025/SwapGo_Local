from datetime import datetime, timezone, timedelta


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()

def kst_now():
    return datetime.now(timezone(timedelta(hours=9)))


_INTERVAL_SEC = {"1m": 60, "5m": 300, "1h": 3600, "1d": 86400}


def candle_bucket_start(ts: datetime, interval: str) -> datetime:
    sec = _INTERVAL_SEC[interval]
    epoch = int(ts.timestamp())
    bucket = epoch - (epoch % sec)
    KST = timezone(timedelta(hours=9))
    return datetime.fromtimestamp(bucket, tz=KST)


def interval_seconds(interval: str) -> int:
    return _INTERVAL_SEC[interval]
