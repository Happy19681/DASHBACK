import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).with_name(".env"))

mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise RuntimeError("MONGO_URI is required. Add it to Api/.env before starting the API.")

client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
db = client[os.getenv("MONGO_DATABASE", "Dashboard-DB")]
collection = db[os.getenv("MONGO_COLLECTION", "Transactions")]
page_records = db[os.getenv("PAGE_RECORDS_COLLECTION", "DashboardPageRecords")]
