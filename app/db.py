from pymongo import MongoClient
import certifi
from .config import settings

client = MongoClient(
    settings.MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where(),
)
db = client[settings.DB_NAME]
licenses = db[settings.COLLECTION_NAME]

