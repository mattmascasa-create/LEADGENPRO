"""
Push notification routes for LeadGen Pro
Handles web push subscriptions and sending push notifications
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime, timezone
import logging
import json

from pywebpush import webpush, WebPushException

from core.config import VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CLAIMS_EMAIL
from core.database import db
from core.security import User, get_current_user

router = APIRouter(prefix="/push", tags=["Push Notifications"])


class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]
    expirationTime: Optional[int] = None


class PushSubscriptionRequest(BaseModel):
    subscription: PushSubscription


@router.get("/vapid-public-key")
async def get_vapid_public_key(current_user: User = Depends(get_current_user)):
    """Get the VAPID public key for push subscription"""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="Push notifications not configured")
    return {"vapid_public_key": VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe_to_push(
    request: PushSubscriptionRequest,
    current_user: User = Depends(get_current_user)
):
    """Subscribe user to push notifications"""
    subscription = request.subscription.model_dump()
    
    await db.push_subscriptions.update_one(
        {"user_id": current_user.id, "endpoint": subscription["endpoint"]},
        {"$set": {
            "user_id": current_user.id,
            "subscription": subscription,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        }},
        upsert=True
    )
    
    await db.notification_preferences.update_one(
        {"user_id": current_user.id},
        {"$set": {"push_enabled": True}},
        upsert=True
    )
    
    return {"success": True, "message": "Push subscription saved"}


@router.post("/unsubscribe")
async def unsubscribe_from_push(
    endpoint: str,
    current_user: User = Depends(get_current_user)
):
    """Unsubscribe user from push notifications"""
    await db.push_subscriptions.delete_one({
        "user_id": current_user.id,
        "endpoint": endpoint
    })
    
    remaining = await db.push_subscriptions.count_documents({"user_id": current_user.id})
    if remaining == 0:
        await db.notification_preferences.update_one(
            {"user_id": current_user.id},
            {"$set": {"push_enabled": False}}
        )
    
    return {"success": True, "message": "Push subscription removed"}


@router.get("/status")
async def get_push_status(current_user: User = Depends(get_current_user)):
    """Get push notification status for current user"""
    subscriptions = await db.push_subscriptions.count_documents({
        "user_id": current_user.id,
        "active": True
    })
    prefs = await db.notification_preferences.find_one({"user_id": current_user.id})
    
    return {
        "push_enabled": prefs.get("push_enabled", False) if prefs else False,
        "active_subscriptions": subscriptions,
        "vapid_configured": bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)
    }


@router.post("/test")
async def send_test_push(current_user: User = Depends(get_current_user)):
    """Send a test push notification to the current user"""
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        raise HTTPException(status_code=500, detail="Push notifications not configured")
    
    subscriptions = await db.push_subscriptions.find({
        "user_id": current_user.id,
        "active": True
    }).to_list(10)
    
    if not subscriptions:
        raise HTTPException(status_code=400, detail="No active push subscriptions found")
    
    success_count = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub["subscription"],
                data=json.dumps({
                    "title": "🔔 Test Notification",
                    "message": "Push notifications are working! You'll receive alerts for hot leads, meetings, and more.",
                    "icon": "/logo192.png",
                    "type": "test"
                }),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"}
            )
            success_count += 1
        except WebPushException as e:
            logging.error(f"Push notification failed: {e}")
            if e.response and e.response.status_code in [404, 410]:
                await db.push_subscriptions.update_one(
                    {"_id": sub["_id"]},
                    {"$set": {"active": False}}
                )
    
    return {
        "success": True,
        "sent": success_count,
        "total_subscriptions": len(subscriptions)
    }


__all__ = ['router']
