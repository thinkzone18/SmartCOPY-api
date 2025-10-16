import os
import sys
import uuid
import requests
from app.config import settings
from app.utils import hash_key, make_expiry
from pymongo import MongoClient

def create_license_key(days_valid=365, metadata=None):
    key = f"SMARTCOPY-{uuid.uuid4().hex[:8].upper()}"
    key_hash = hash_key(key)
    expiry = make_expiry(days_valid)
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.DB_NAME]
    coll = db[settings.COLLECTION_NAME]
    coll.insert_one({
        "key_hash": key_hash,
        "expiry": expiry,
        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        "metadata": metadata or {},
        "active": True
    })
    return key, expiry

if __name__ == "__main__":
    days = 365
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    key, expiry = create_license_key(days)
    print("New key:", key)
    print("Expiry:", expiry)
