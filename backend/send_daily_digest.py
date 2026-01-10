#!/usr/bin/env python3
"""
Daily Digest Email Cron Job
Sends daily digest emails to all users with email_digest enabled

This script is designed to be run by cron at a scheduled time (e.g., 8 AM daily).
Usage: python send_daily_digest.py

Cron example (run daily at 8 AM):
0 8 * * * cd /app/backend && /root/.venv/bin/python send_daily_digest.py >> /var/log/digest_cron.log 2>&1
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add backend directory to path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / '.env')

from motor.motor_asyncio import AsyncIOMotorClient
import resend
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'LeadGen Pro <onboarding@resend.dev>')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')


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


async def send_daily_digests():
    """Send daily digest emails to all users with email_digest enabled"""
    
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY not configured. Cannot send emails.")
        return {"success": False, "error": "Email service not configured"}
    
    resend.api_key = RESEND_API_KEY
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Find all users with email digest enabled
        prefs_with_digest = await db.notification_preferences.find({
            "email_digest": True
        }).to_list(1000)
        
        if not prefs_with_digest:
            logger.info("No users have email digest enabled.")
            return {"success": True, "sent": 0, "failed": 0, "total_eligible": 0}
        
        user_ids = [p["user_id"] for p in prefs_with_digest]
        users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0}).to_list(1000)
        
        logger.info(f"Found {len(users)} users with email digest enabled")
        
        sent_count = 0
        failed_count = 0
        
        for user_doc in users:
            try:
                # Get user's notifications from last 24 hours
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
                
                result = resend.Emails.send(params)
                
                # Log the digest send
                await db.digest_logs.insert_one({
                    "user_id": user_doc["id"],
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "notifications_count": len(notifications),
                    "email_id": result.get("id") if isinstance(result, dict) else str(result),
                    "source": "cron"
                })
                
                sent_count += 1
                logger.info(f"Sent digest to {user_doc['email']} ({len(notifications)} notifications)")
                
            except Exception as e:
                logger.error(f"Failed to send digest to {user_doc.get('email')}: {e}")
                failed_count += 1
        
        result = {
            "success": True,
            "sent": sent_count,
            "failed": failed_count,
            "total_eligible": len(users),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Daily digest complete: {result}")
        return result
        
    finally:
        client.close()


if __name__ == "__main__":
    logger.info("Starting daily digest cron job...")
    result = asyncio.run(send_daily_digests())
    logger.info(f"Cron job complete: {result}")
    
    # Exit with appropriate code
    if result.get("success"):
        sys.exit(0)
    else:
        sys.exit(1)
