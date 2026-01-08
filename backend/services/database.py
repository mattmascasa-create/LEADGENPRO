"""
Database Service - MongoDB Connection and Database Instance
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB setup
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'leadgen_pro')

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

def get_database():
    """Get the database instance"""
    return db

def get_client():
    """Get the MongoDB client"""
    return client
