"""
Database connection and utilities for LeadGen Pro
"""
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_URL, DB_NAME

# MongoDB client
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collection references for convenience
users_collection = db.users
leads_collection = db.leads
activities_collection = db.activities
appointments_collection = db.appointments
call_logs_collection = db.call_logs
calendar_events_collection = db.calendar_events
chat_messages_collection = db.chat_messages
notifications_collection = db.notifications
push_subscriptions_collection = db.push_subscriptions
notification_preferences_collection = db.notification_preferences
