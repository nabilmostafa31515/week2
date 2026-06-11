import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

def _get_uri():
    # Streamlit Cloud secrets
    try:
        import streamlit as st
        if "MONGO_URI" in st.secrets:
            return st.secrets["MONGO_URI"]
    except Exception:
        pass
    # local .env fallback
    return os.getenv("MONGO_URI")

def get_client():
    uri = _get_uri()
    if not uri:
        raise RuntimeError(
            "MONGO_URI is not set. Add it to your .env file "
            "(local) or Streamlit Secrets (cloud)."
        )
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client

def get_db(db_name: str = "kayfa_analytics"):
    client = get_client()
    return client[db_name]
