"""
Notification routes for LeadGen Pro
Handles smart notifications, push notifications, preferences, and email digests
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
from ..core.security import User, get_current_user, is_admin_user

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


# ==================== NOTIFICATION ENDPOINTS ====================

@router.get("")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get user's smart notifications"""
    query = {"user_id": current_user.id}
    if unread_only:
        query["read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    unread_count = await db.notifications.count_documents({
        "user_id": current_user.id, "read": False
    })
    
    return {
        "notifications": notifications,
        "unread_count": unread_count
    }


@router.post("/mark-read")
async def mark_notifications_read(
    notification_ids: List[str] = None,
    mark_all: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Mark notifications as read"""
    if mark_all:
        await db.notifications.update_many(
            {"user_id": current_user.id, "read": False},
            {"$set": {"read": True}}
        )
        return {"success": True, "message": "All notifications marked as read"}
    
    if notification_ids:
        await db.notifications.update_many(
            {"id": {"$in": notification_ids}, "user_id": current_user.id},
            {"$set": {"read": True}}
        )
        return {"success": True, "message": f"{len(notification_ids)} notifications marked as read"}
    
    return {"success": False, "message": "No notifications specified"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a notification"""
    result = await db.notifications.delete_one({
        "id": notification_id, "user_id": current_user.id
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.get("/generate")
async def generate_smart_notifications(current_user: User = Depends(get_current_user)):
    """Generate smart notifications based on current data"""
    notifications_created = []
    push_notifications_sent = 0
    now = datetime.now(timezone.utc)
    
    prefs = await db.notification_preferences.find_one({"user_id": current_user.id}) or {}
    push_enabled = prefs.get("push_enabled", False)
    
    async def create_notification_with_push(notif: SmartNotification):
        nonlocal push_notifications_sent
        doc = notif.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.notifications.insert_one(doc)
        notifications_created.append(notif.title)
        
        if push_enabled:
            sent = await send_push_to_user(
                user_id=notif.user_id,
                title=notif.title,
                message=notif.message,
                data={
                    "type": notif.type,
                    "lead_id": notif.lead_id,
                    "id": notif.id
                }
            )
            push_notifications_sent += sent
    
    # 1. Hot Leads
    if prefs.get("hot_lead_alerts", True):
        hot_leads_query = {"assigned_to": current_user.id} if not is_admin_user(current_user) else {}
        hot_leads_query.update({
            "score": {"$gte": 70},
            "$or": [
                {"last_contacted": None},
                {"last_contacted": {"$lt": (now - timedelta(days=3)).isoformat()}}
            ]
        })
        hot_leads = await db.leads.find(hot_leads_query, {"_id": 0}).to_list(10)
        
        for lead in hot_leads:
            existing = await db.notifications.find_one({
                "user_id": current_user.id,
                "lead_id": lead["id"],
                "type": NotificationType.HOT_LEAD,
                "created_at": {"$gte": (now - timedelta(hours=24)).isoformat()}
            })
            if not existing:
                notif = SmartNotification(
                    user_id=current_user.id,
                    type=NotificationType.HOT_LEAD,
                    title="🔥 Hot Lead Needs Attention",
                    message=f"{lead['first_name']} {lead['last_name']} ({lead['company']}) has a score of {lead['score']} but hasn't been contacted recently.",
                    lead_id=lead["id"],
                    data={"score": lead["score"], "company": lead["company"]}
                )
                await create_notification_with_push(notif)
    
    # 2. Stale Deals
    if prefs.get("stale_deal_alerts", True):
        stale_query = {"assigned_to": current_user.id} if not is_admin_user(current_user) else {}
        stale_query.update({
            "stage": {"$in": ["proposal", "negotiation"]},
            "updated_at": {"$lt": (now - timedelta(days=7)).isoformat()}
        })
        stale_deals = await db.leads.find(stale_query, {"_id": 0}).to_list(10)
        
        for lead in stale_deals:
            existing = await db.notifications.find_one({
                "user_id": current_user.id,
                "lead_id": lead["id"],
                "type": NotificationType.STALE_DEAL,
                "created_at": {"$gte": (now - timedelta(days=3)).isoformat()}
            })
            if not existing:
                deal_value = lead.get("deal_value", 0)
                notif = SmartNotification(
                    user_id=current_user.id,
                    type=NotificationType.STALE_DEAL,
                    title="⚠️ Stale Deal Alert",
                    message=f"Deal with {lead['company']} (${deal_value:,.0f}) has been in {lead['stage']} for over a week.",
                    lead_id=lead["id"],
                    data={"stage": lead["stage"], "deal_value": deal_value}
                )
                await create_notification_with_push(notif)
    
    # 3. Upcoming Meetings
    if prefs.get("meeting_reminders", True):
        upcoming_meetings = await db.calendar_events.find({
            "created_by": current_user.id,
            "start": {
                "$gte": now.isoformat(),
                "$lte": (now + timedelta(hours=1)).isoformat()
            }
        }, {"_id": 0}).to_list(10)
        
        for meeting in upcoming_meetings:
            existing = await db.notifications.find_one({
                "user_id": current_user.id,
                "type": NotificationType.MEETING_REMINDER,
                "data.event_id": meeting["id"],
                "created_at": {"$gte": (now - timedelta(hours=2)).isoformat()}
            })
            if not existing:
                notif = SmartNotification(
                    user_id=current_user.id,
                    type=NotificationType.MEETING_REMINDER,
                    title="📅 Meeting Starting Soon",
                    message=f"'{meeting['title']}' starts in less than an hour.",
                    data={"event_id": meeting["id"], "title": meeting["title"]}
                )
                await create_notification_with_push(notif)
    
    # 4. Tasks Due Today
    if prefs.get("task_due_alerts", True):
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        due_tasks = await db.tasks.find({
            "assigned_to": current_user.id,
            "status": {"$ne": "completed"},
            "due_date": {
                "$gte": today_start.isoformat(),
                "$lte": today_end.isoformat()
            }
        }, {"_id": 0}).to_list(10)
        
        for task in due_tasks:
            existing = await db.notifications.find_one({
                "user_id": current_user.id,
                "type": NotificationType.TASK_DUE,
                "data.task_id": task.get("id"),
                "created_at": {"$gte": today_start.isoformat()}
            })
            if not existing:
                notif = SmartNotification(
                    user_id=current_user.id,
                    type=NotificationType.TASK_DUE,
                    title="✅ Task Due Today",
                    message=f"'{task.get('title', 'Task')}' is due today.",
                    data={"task_id": task.get("id"), "title": task.get("title")}
                )
                await create_notification_with_push(notif)
    
    return {
        "success": True,
        "notifications_created": len(notifications_created),
        "push_notifications_sent": push_notifications_sent,
        "details": notifications_created
    }


# ==================== NOTIFICATION PREFERENCES ====================

@router.get("/preferences")
async def get_notification_preferences(current_user: User = Depends(get_current_user)):
    """Get user's notification preferences"""
    prefs = await db.notification_preferences.find_one({"user_id": current_user.id})
    
    if not prefs:
        return NotificationPreferences().model_dump()
    
    prefs.pop("_id", None)
    prefs.pop("user_id", None)
    return prefs


@router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_user)
):
    """Update user's notification preferences"""
    prefs_dict = preferences.model_dump()
    prefs_dict["user_id"] = current_user.id
    prefs_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.notification_preferences.update_one(
        {"user_id": current_user.id},
        {"$set": prefs_dict},
        upsert=True
    )
    
    return {"success": True, "message": "Notification preferences updated"}


# ==================== EMAIL OPEN TRACKING ====================

@router.post("/email-opened")
async def create_email_opened_notification(
    lead_id: str,
    email_subject: str,
    background_tasks: BackgroundTasks
):
    """Create notification when lead opens an email"""
    lead = await db.leads.find_one({"id": lead_id})
    if not lead or not lead.get("assigned_to"):
        return {"success": False}
    
    user_id = lead["assigned_to"]
    
    if not await should_send_notification(user_id, NotificationType.EMAIL_OPENED):
        return {"success": False, "reason": "User disabled email open alerts"}
    
    notif = SmartNotification(
        user_id=user_id,
        type=NotificationType.EMAIL_OPENED,
        title="📧 Email Opened!",
        message=f"{lead['first_name']} {lead['last_name']} opened your email: '{email_subject[:50]}...'",
        lead_id=lead_id,
        data={"subject": email_subject, "company": lead.get("company")}
    )
    
    doc = notif.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.notifications.insert_one(doc)
    
    await send_push_to_user(
        user_id=user_id,
        title=notif.title,
        message=notif.message,
        data={"type": notif.type, "lead_id": lead_id}
    )
    
    return {"success": True}


# ==================== DAILY DIGEST ====================

@router.post("/send-digest")
async def send_daily_digest(current_user: User = Depends(get_current_user)):
    """Send daily digest email to the current user"""
    if not RESEND_API_KEY:
        raise HTTPException(status_code=500, detail="Email service not configured")
    
    prefs = await db.notification_preferences.find_one({"user_id": current_user.id})
    if prefs and not prefs.get("email_digest", False):
        return {"success": False, "message": "Email digest is disabled in your preferences"}
    
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    notifications = await db.notifications.find({
        "user_id": current_user.id,
        "created_at": {"$gte": yesterday.isoformat()}
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    unread_count = await db.notifications.count_documents({
        "user_id": current_user.id,
        "read": False
    })
    
    stats = {"unread": unread_count}
    user_name = current_user.full_name or current_user.email.split('@')[0]
    html_content = generate_digest_html(
        user_name=user_name,
        notifications=notifications,
        stats=stats,
        frontend_url=FRONTEND_URL
    )
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [current_user.email],
            "subject": f"☀️ Your Daily Sales Digest - {len(notifications)} notifications",
            "html": html_content
        }
        
        result = await asyncio.to_thread(resend.Emails.send, params)
        
        await db.digest_logs.insert_one({
            "user_id": current_user.id,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "notifications_count": len(notifications),
            "email_id": result.get("id") if isinstance(result, dict) else str(result)
        })
        
        return {
            "success": True,
            "message": f"Daily digest sent to {current_user.email}",
            "notifications_included": len(notifications)
        }
        
    except Exception as e:
        logging.error(f"Failed to send digest email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.post("/send-digest-all")
async def send_digest_to_all_users(current_user: User = Depends(get_current_user)):
    """Send daily digest to all users with email_digest enabled (admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not RESEND_API_KEY:
        raise HTTPException(status_code=500, detail="Email service not configured")
    
    prefs_with_digest = await db.notification_preferences.find({
        "email_digest": True
    }).to_list(100)
    
    user_ids = [p["user_id"] for p in prefs_with_digest]
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0}).to_list(100)
    
    sent_count = 0
    failed_count = 0
    
    for user_doc in users:
        try:
            yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
            notifications = await db.notifications.find({
                "user_id": user_doc["id"],
                "created_at": {"$gte": yesterday.isoformat()}
            }, {"_id": 0}).to_list(50)
            
            unread_count = await db.notifications.count_documents({
                "user_id": user_doc["id"],
                "read": False
            })
            
            user_name = user_doc.get("full_name") or user_doc["email"].split('@')[0]
            html_content = generate_digest_html(
                user_name=user_name,
                notifications=notifications,
                stats={"unread": unread_count},
                frontend_url=FRONTEND_URL
            )
            
            params = {
                "from": SENDER_EMAIL,
                "to": [user_doc["email"]],
                "subject": f"☀️ Your Daily Sales Digest - {len(notifications)} notifications",
                "html": html_content
            }
            
            await asyncio.to_thread(resend.Emails.send, params)
            sent_count += 1
            
        except Exception as e:
            logging.error(f"Failed to send digest to {user_doc.get('email')}: {e}")
            failed_count += 1
    
    return {
        "success": True,
        "sent": sent_count,
        "failed": failed_count,
        "total_eligible": len(users)
    }


@router.get("/digest-preview")
async def preview_daily_digest(current_user: User = Depends(get_current_user)):
    """Preview the daily digest email content"""
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    notifications = await db.notifications.find({
        "user_id": current_user.id,
        "created_at": {"$gte": yesterday.isoformat()}
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    unread_count = await db.notifications.count_documents({
        "user_id": current_user.id,
        "read": False
    })
    
    user_name = current_user.full_name or current_user.email.split('@')[0]
    html_content = generate_digest_html(
        user_name=user_name,
        notifications=notifications,
        stats={"unread": unread_count},
        frontend_url=FRONTEND_URL
    )
    
    return Response(content=html_content, media_type="text/html")


# ==================== LEAD ASSIGNED NOTIFICATION (Helper) ====================

async def create_lead_assigned_notification(lead: dict, assigned_to: str):
    """Create notification when a lead is assigned to a user"""
    if not await should_send_notification(assigned_to, NotificationType.NEW_LEAD_ASSIGNED):
        return
    
    notif = SmartNotification(
        user_id=assigned_to,
        type=NotificationType.NEW_LEAD_ASSIGNED,
        title="👤 New Lead Assigned",
        message=f"You've been assigned {lead['first_name']} {lead['last_name']} from {lead.get('company', 'Unknown')}",
        lead_id=lead["id"],
        data={
            "company": lead.get("company"),
            "deal_value": lead.get("deal_value", 0),
            "score": lead.get("score", 0)
        }
    )
    
    doc = notif.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.notifications.insert_one(doc)
    
    await send_push_to_user(
        user_id=assigned_to,
        title=notif.title,
        message=notif.message,
        data={"type": notif.type, "lead_id": lead["id"]}
    )


# Export for use in main server
__all__ = [
    'router',
    'NotificationType',
    'SmartNotification',
    'NotificationPreferences',
    'PushSubscription',
    'PushSubscriptionRequest',
    'send_push_to_user',
    'should_send_notification',
    'generate_digest_html',
    'create_lead_assigned_notification'
]
