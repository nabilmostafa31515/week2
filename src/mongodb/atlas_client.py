import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════
#  CONNECTION
# ══════════════════════════════════════════════════════

def get_client():
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise RuntimeError(
            "MONGO_URI is not set. Add it to your .env file "
            "(see .env.example)."
        )
    # never log the URI — it contains credentials
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client

def get_db(db_name: str = "kayfa_analytics"):
    client = get_client()
    return client[db_name]