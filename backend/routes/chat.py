"""
Chat routes for LeadGen Pro
Handles team chat channels, messages, DMs, reactions, threads, and user presence/status
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

from core.database import db
from core.security import User, get_current_user, is_admin_user

router = APIRouter(prefix="/chat", tags=["Chat"])


# ==================== MODELS ====================

class Channel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    type: str = "public"  # public, private, dm
    participants: Optional[List[str]] = None  # For DMs - list of user IDs
    participant_names: Optional[dict] = None  # For DMs - {user_id: name}
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "public"


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    sender_id: str
    sender_name: str
    content: str
    type: str = "text"  # text, file, meeting
    metadata: Optional[Dict[str, Any]] = None
    reactions: Optional[Dict[str, List[str]]] = None
    reply_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessageCreate(BaseModel):
    channel_id: str
    content: str
    type: str = "text"
    metadata: Optional[Dict[str, Any]] = None


class UserStatus(BaseModel):
    user_id: str
    status: str = "online"  # online, away, busy, offline
    status_emoji: Optional[str] = None
    status_text: Optional[str] = None
    expires_at: Optional[str] = None
    last_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UpdateStatusRequest(BaseModel):
    status: str  # online, away, busy, offline, or custom
    status_emoji: Optional[str] = None
    status_text: Optional[str] = None
    duration_minutes: Optional[int] = None


# Status presets
STATUS_PRESETS = {
    "online": {"emoji": "🟢", "text": "Online", "color": "green"},
    "away": {"emoji": "🟡", "text": "Away", "color": "yellow"},
    "busy": {"emoji": "🔴", "text": "Busy", "color": "red"},
    "offline": {"emoji": "⚫", "text": "Offline", "color": "gray"},
    "lunch": {"emoji": "🍕", "text": "At Lunch", "color": "orange"},
    "wfh": {"emoji": "🏠", "text": "Working from Home", "color": "blue"},
    "vacation": {"emoji": "🏖️", "text": "On Vacation", "color": "purple"},
    "meeting": {"emoji": "📅", "text": "In a Meeting", "color": "blue"},
    "sick": {"emoji": "🤒", "text": "Out Sick", "color": "gray"},
    "focus": {"emoji": "🎯", "text": "Focus Time", "color": "red"},
    "commuting": {"emoji": "🚗", "text": "Commuting", "color": "yellow"},
    "brb": {"emoji": "⏰", "text": "Be Right Back", "color": "yellow"}
}


# ==================== CHANNEL ENDPOINTS ====================

@router.get("/channels", response_model=List[Channel])
async def get_channels(current_user: User = Depends(get_current_user)):
    """Get all channels including DMs for current user"""
    # Get public channels
    public_channels = await db.channels.find({"type": "public"}, {"_id": 0}).to_list(1000)
    
    # Get DM channels where user is a participant
    dm_channels = await db.channels.find({
        "type": "dm",
        "participants": current_user.id
    }, {"_id": 0}).to_list(100)
    
    # Create default public channels if none exist
    if not public_channels:
        default_channels = [
            Channel(name="general", description="General discussion", type="public", created_by="system"),
            Channel(name="sales", description="Sales team discussions", type="public", created_by="system"),
            Channel(name="random", description="Off-topic chat", type="public", created_by="system")
        ]
        for channel in default_channels:
            doc = channel.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.channels.insert_one(doc)
        public_channels = [c.model_dump() for c in default_channels]
    
    all_channels = public_channels + dm_channels
    return [Channel(**c) for c in all_channels]


@router.post("/channels", response_model=Channel)
async def create_channel(channel_data: ChannelCreate, current_user: User = Depends(get_current_user)):
    """Create a new channel"""
    channel = Channel(**channel_data.model_dump(), created_by=current_user.id)
    doc = channel.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.channels.insert_one(doc)
    return channel


@router.post("/dm/{user_id}")
async def create_or_get_dm(user_id: str, current_user: User = Depends(get_current_user)):
    """Create or get a DM channel with a user"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot create DM with yourself")
    
    # Check if DM already exists
    existing = await db.channels.find_one({
        "type": "dm",
        "participants": {"$all": [current_user.id, user_id]}
    }, {"_id": 0})
    
    if existing:
        return Channel(**existing)
    
    # Get other user's info
    other_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create new DM channel
    channel = Channel(
        name=f"dm-{current_user.id}-{user_id}",
        type="dm",
        participants=[current_user.id, user_id],
        participant_names={
            current_user.id: current_user.full_name,
            user_id: other_user.get("full_name", "Unknown")
        },
        created_by=current_user.id
    )
    
    doc = channel.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.channels.insert_one(doc)
    
    return channel


@router.get("/dm/list")
async def list_dm_channels(current_user: User = Depends(get_current_user)):
    """Get all DM channels for current user with last message info"""
    dm_channels = await db.channels.find({
        "type": "dm",
        "participants": current_user.id
    }, {"_id": 0}).to_list(100)
    
    result = []
    for channel in dm_channels:
        # Get last message
        last_msg = await db.chat_messages.find_one(
            {"channel_id": channel["id"]},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        # Get unread count
        unread = await db.chat_messages.count_documents({
            "channel_id": channel["id"],
            "sender_id": {"$ne": current_user.id},
            "read_by": {"$nin": [current_user.id]}
        })
        
        # Get other participant's info
        other_id = [p for p in channel.get("participants", []) if p != current_user.id][0] if channel.get("participants") else None
        other_user = None
        if other_id:
            other_user = await db.users.find_one({"id": other_id}, {"_id": 0, "password": 0})
        
        result.append({
            **channel,
            "last_message": last_msg,
            "unread_count": unread,
            "other_user": other_user
        })
    
    return result


# ==================== MESSAGE ENDPOINTS ====================

@router.get("/messages/{channel_id}", response_model=List[ChatMessage])
async def get_messages(channel_id: str, limit: int = 50, current_user: User = Depends(get_current_user)):
    """Get messages from a channel"""
    messages = await db.chat_messages.find(
        {"channel_id": channel_id}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Mark messages as read
    await db.chat_messages.update_many(
        {"channel_id": channel_id, "sender_id": {"$ne": current_user.id}},
        {"$addToSet": {"read_by": current_user.id}}
    )
    
    return [ChatMessage(**msg) for msg in reversed(messages)]


@router.post("/messages", response_model=ChatMessage)
async def send_message(msg_data: ChatMessageCreate, current_user: User = Depends(get_current_user)):
    """Send a message to a channel"""
    message = ChatMessage(
        **msg_data.model_dump(),
        sender_id=current_user.id,
        sender_name=current_user.full_name
    )
    doc = message.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['read_by'] = [current_user.id]
    await db.chat_messages.insert_one(doc)
    
    # Check for @mentions and create notifications
    if "@" in msg_data.content:
        import re
        mentions = re.findall(r'@(\w+)', msg_data.content)
        for mention in mentions:
            mentioned_user = await db.users.find_one(
                {"full_name": {"$regex": mention, "$options": "i"}},
                {"_id": 0}
            )
            if mentioned_user:
                # Create notification
                await db.notifications.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": mentioned_user["id"],
                    "type": "mention",
                    "title": f"💬 {current_user.full_name} mentioned you",
                    "message": f"In #{msg_data.channel_id}: {msg_data.content[:100]}...",
                    "read": False,
                    "data": {"channel_id": msg_data.channel_id, "message_id": message.id},
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
    
    return message


@router.post("/messages/{message_id}/reactions")
async def add_reaction(
    message_id: str,
    reaction: dict,
    current_user: User = Depends(get_current_user)
):
    """Add a reaction to a message"""
    emoji = reaction.get("emoji")
    if not emoji:
        raise HTTPException(status_code=400, detail="Emoji is required")
    
    message = await db.chat_messages.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    reactions = message.get("reactions", {})
    if emoji not in reactions:
        reactions[emoji] = []
    
    if current_user.id not in reactions[emoji]:
        reactions[emoji].append(current_user.id)
    else:
        reactions[emoji].remove(current_user.id)
        if not reactions[emoji]:
            del reactions[emoji]
    
    await db.chat_messages.update_one(
        {"id": message_id},
        {"$set": {"reactions": reactions}}
    )
    
    return {"reactions": reactions}


@router.post("/messages/{message_id}/thread")
async def reply_to_thread(
    message_id: str,
    msg_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user)
):
    """Reply to a message thread"""
    parent = await db.chat_messages.find_one({"id": message_id})
    if not parent:
        raise HTTPException(status_code=404, detail="Parent message not found")
    
    message = ChatMessage(
        **msg_data.model_dump(),
        sender_id=current_user.id,
        sender_name=current_user.full_name,
        metadata={
            **(msg_data.metadata or {}),
            "thread_id": message_id,
            "reply_to": message_id
        }
    )
    doc = message.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.chat_messages.insert_one(doc)
    
    await db.chat_messages.update_one(
        {"id": message_id},
        {"$inc": {"reply_count": 1}}
    )
    
    return message


@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, current_user: User = Depends(get_current_user)):
    """Delete a message - only author or admin can delete"""
    message = await db.chat_messages.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message["sender_id"] != current_user.id and not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to delete this message")
    
    await db.chat_messages.delete_one({"id": message_id})
    return {"message": "Message deleted"}


# Export models
__all__ = [
    'router',
    'Channel',
    'ChannelCreate',
    'ChatMessage',
    'ChatMessageCreate',
    'UserStatus',
    'UpdateStatusRequest',
    'STATUS_PRESETS'
]
