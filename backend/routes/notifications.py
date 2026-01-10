"""
Notification routes for LeadGen Pro
Handles smart notifications, push notifications, and email digests
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging
import json
import asyncio

from pywebpush import webpush, WebPushException
import resend

from ..core.config import (
    VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CLAIMS_EMAIL,
    RESEND_API_KEY, SENDER_EMAIL, FRONTEND_URL
)
from ..core.database import db

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# ==================== MODELS ====================

class NotificationType:
    HOT_LEAD = "hot_lead"
    STALE_DEAL = "stale_deal"
    EMAIL_OPENED = "email_opened"
    MEETING_REMINDER = "meeting_reminder"
    TASK_DUE = "task_due"
    NEW_LEAD_ASSIGNED = "new_lead_assigned"
    DEAL_STAGE_CHANGE = "deal_stage_change"

class SmartNotification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str
    title: str
    message: str
    lead_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NotificationPreferences(BaseModel):
    hot_lead_alerts: bool = True
    stale_deal_alerts: bool = True
    email_opened_alerts: bool = True
    meeting_reminders: bool = True
    task_due_alerts: bool = True
    new_lead_assigned: bool = True
    deal_stage_change: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    email_digest: bool = False
    push_enabled: bool = False

class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]
    expirationTime: Optional[int] = None

class PushSubscriptionRequest(BaseModel):
    subscription: PushSubscription

# ==================== HELPER FUNCTIONS ====================

async def send_push_to_user(user_id: str, title: str, message: str, data: dict = None) -> int:
    """Send push notification to all active subscriptions for a user"""
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        return 0
    
    subscriptions = await db.push_subscriptions.find({
        "user_id": user_id,
        "active": True
    }).to_list(10)
    
    if not subscriptions:
        return 0
    
    payload = {
        "title": title,
        "message": message,
        "icon": "/logo192.png",
        **(data or {})
    }
    
    success_count = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub["subscription"],
                data=json.dumps(payload),
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
    
    return success_count

async def should_send_notification(user_id: str, notification_type: str) -> bool:
    """Check if user should receive this notification type based on preferences"""
    prefs = await db.notification_preferences.find_one({"user_id": user_id})
    
    if not prefs:
        return True
    
    # Check quiet hours
    if prefs.get("quiet_hours_enabled", False):
        now = datetime.now(timezone.utc)
        current_time = now.strftime("%H:%M")
        start = prefs.get("quiet_hours_start", "22:00")
        end = prefs.get("quiet_hours_end", "08:00")
        
        if start > end:
            if current_time >= start or current_time < end:
                return False
        else:
            if start <= current_time < end:
                return False
    
    type_to_pref = {
        NotificationType.HOT_LEAD: "hot_lead_alerts",
        NotificationType.STALE_DEAL: "stale_deal_alerts",
        NotificationType.EMAIL_OPENED: "email_opened_alerts",
        NotificationType.MEETING_REMINDER: "meeting_reminders",
        NotificationType.TASK_DUE: "task_due_alerts",
        NotificationType.NEW_LEAD_ASSIGNED: "new_lead_assigned",
        NotificationType.DEAL_STAGE_CHANGE: "deal_stage_change",
    }
    
    pref_key = type_to_pref.get(notification_type)
    if pref_key:
        return prefs.get(pref_key, True)
    
    return True

def generate_digest_html(user_name: str, notifications: list, stats: dict, frontend_url: str) -> str:
    """Generate beautiful HTML email for daily digest"""
    
    hot_leads = [n for n in notifications if n.get('type') == 'hot_lead']
    stale_deals = [n for n in notifications if n.get('type') == 'stale_deal']
    tasks_due = [n for n in notifications if n.get('type') == 'task_due']
    meetings = [n for n in notifications if n.get('type') == 'meeting_reminder']
    other = [n for n in notifications if n.get('type') not in ['hot_lead', 'stale_deal', 'task_due', 'meeting_reminder']]
    
    def notification_section(title: str, emoji: str, items: list, color: str) -> str:
        if not items:
            return ""
        items_html = "".join([
            f'<li style="padding: 8px 0; border-bottom: 1px solid #f0f0f0;">{n.get("message", "")}</li>'
            for n in items[:5]
        ])
        return f'''
        <div style="margin-bottom: 24px;">
            <h3 style="color: {color}; margin: 0 0 12px 0; font-size: 16px;">
                {emoji} {title} ({len(items)})
            </h3>
            <ul style="margin: 0; padding-left: 20px; color: #555;">
                {items_html}
            </ul>
            {"<p style='color: #888; font-size: 12px;'>... and " + str(len(items) - 5) + " more</p>" if len(items) > 5 else ""}
        </div>
        '''
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); border-radius: 12px 12px 0 0; padding: 32px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">Good Morning, {user_name}!</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0;">Here's your daily sales digest</p>
            </div>
            
            <div style="background: white; padding: 24px; border-left: 1px solid #e5e5e5; border-right: 1px solid #e5e5e5;">
                <div style="display: flex; text-align: center; border-bottom: 1px solid #f0f0f0; padding-bottom: 20px; margin-bottom: 20px;">
                    <div style="flex: 1;">
                        <div style="font-size: 32px; font-weight: bold; color: #1e40af;">{stats.get('unread', 0)}</div>
                        <div style="color: #666; font-size: 12px;">Unread Alerts</div>
                    </div>
                    <div style="flex: 1;">
                        <div style="font-size: 32px; font-weight: bold; color: #f59e0b;">{len(hot_leads)}</div>
                        <div style="color: #666; font-size: 12px;">Hot Leads</div>
                    </div>
                    <div style="flex: 1;">
                        <div style="font-size: 32px; font-weight: bold; color: #10b981;">{len(tasks_due)}</div>
                        <div style="color: #666; font-size: 12px;">Tasks Due</div>
                    </div>
                </div>
                
                {notification_section("Hot Leads Need Attention", "🔥", hot_leads, "#f59e0b")}
                {notification_section("Stale Deals", "⚠️", stale_deals, "#eab308")}
                {notification_section("Tasks Due Today", "✅", tasks_due, "#10b981")}
                {notification_section("Upcoming Meetings", "📅", meetings, "#8b5cf6")}
                {notification_section("Other Notifications", "📬", other, "#6b7280")}
                
                {'<p style="color: #888; text-align: center; padding: 20px;">No new notifications overnight! All caught up!</p>' if not notifications else ""}
            </div>
            
            <div style="background: white; padding: 24px; text-align: center; border-left: 1px solid #e5e5e5; border-right: 1px solid #e5e5e5;">
                <a href="{frontend_url}/dashboard" style="display: inline-block; background: #1e40af; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    Open Dashboard
                </a>
            </div>
            
            <div style="background: #f9fafb; border-radius: 0 0 12px 12px; padding: 20px; text-align: center; border: 1px solid #e5e5e5; border-top: none;">
                <p style="color: #888; font-size: 12px; margin: 0;">
                    You're receiving this because you enabled Daily Digest in your notification settings.
                    <br>
                    <a href="{frontend_url}/settings/notifications" style="color: #1e40af;">Manage preferences</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

# Note: get_current_user will be imported from the main server.py or auth module
# For now, these routes will be integrated into the main server.py

# Export for use in main server
__all__ = [
    'NotificationType',
    'SmartNotification', 
    'NotificationPreferences',
    'PushSubscription',
    'PushSubscriptionRequest',
    'send_push_to_user',
    'should_send_notification',
    'generate_digest_html',
    'router'
]
