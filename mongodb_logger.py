import pymongo
from datetime import datetime, timezone
import os

# MongoDB connection
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
client = pymongo.MongoClient(MONGODB_URI)
db = client.get_database("data_donation_tracker")

# Collections
user_actions = db["user_actions"]
chatgpt_messages = db["chatgpt_messages"]

def log_user_action(user_id, action, status, failure_reason=None, metadata=None):
    """Log user action to MongoDB."""
    doc = {
        "timestamp": datetime.now(timezone.utc),
        "user_id": user_id,
        "action": action,  # "upload", "verification"
        "status": status,  # "success", "failure"
        "failure_reason": failure_reason,
        "metadata": metadata or {}
    }
    user_actions.insert_one(doc)
    return doc

def store_message_ids(user_id, message_ids):
    """Store message IDs for a user."""
    if not message_ids:
        return
    docs = [{"user_id": user_id, "message_id": msg_id, "timestamp": datetime.now(timezone.utc)}
            for msg_id in message_ids]
    chatgpt_messages.insert_many(docs)

def get_user_message_ids(user_id):
    """Get all message IDs for a user."""
    cursor = chatgpt_messages.find({"user_id": user_id}, {"message_id": 1})
    return set(doc["message_id"] for doc in cursor)

def get_all_message_ids():
    """Get all message IDs across users."""
    cursor = chatgpt_messages.find({}, {"message_id": 1, "user_id": 1})
    # Return mapping message_id -> set of user_ids
    mapping = {}
    for doc in cursor:
        mapping.setdefault(doc["message_id"], set()).add(doc["user_id"])
    return mapping

def compute_overlap(user_id):
    """Compute message ID overlap percentage with other users."""
    user_msgs = get_user_message_ids(user_id)
    if not user_msgs:
        return 0.0
    mapping = get_all_message_ids()
    overlapping = 0
    for msg_id in user_msgs:
        users = mapping.get(msg_id, set())
        if len(users) > 1:  # This message appears in at least one other user
            overlapping += 1
    return (overlapping / len(user_msgs)) * 100.0