import hashlib
from datetime import date, datetime, timedelta

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

def make_expiry(days: int = 365) -> str:
    return (date.today() + timedelta(days=days)).isoformat()

def is_expired(expiry_iso: str) -> bool:
    try:
        exp = datetime.fromisoformat(expiry_iso).date()
        return date.today() > exp
    except Exception:
        return True
