#!/usr/bin/env python3
"""
Daily Digest Cron Job for LeadGen Pro
Run this script via cron at 8 AM daily to send digest emails to all users with email_digest enabled.

Cron entry (add to crontab):
0 8 * * * /usr/bin/python3 /app/backend/cron/daily_digest.py >> /var/log/leadgen_digest.log 2>&1

Or for testing, run manually:
python3 /app/backend/cron/daily_digest.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import resend

# Configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'leadgen_pro')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'LeadGen Pro <onboarding@resend.dev>')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://crm-commander-1.preview.emergentagent.com')

def generate_digest_html(user_name: str, notifications: list, stats: dict) -> str:
    """Generate HTML email for daily digest"""
    
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
        more_text = f"<p style='color: #888; font-size: 12px;'>... and {len(items) - 5} more</p>" if len(items) > 5 else ""
        return f'''
        <div style="margin-bottom: 24px;">
            <h3 style="color: {color}; margin: 0 0 12px 0; font-size: 16px;">
                {emoji} {title} ({len(items)})
            </h3>
            <ul style="margin: 0; padding-left: 20px; color: #555;">
                {items_html}
            </ul>
            {more_text}
        </div>
        '''
    
    no_notifs_msg = '<p style="color: #888; text-align: center; padding: 20px;">No new notifications overnight! All caught up!</p>' if not notifications else ""
    
    return f'''
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
                
                {no_notifs_msg}
            </div>
            
            <div style="background: white; padding: 24px; text-align: center; border-left: 1px solid #e5e5e5; border-right: 1px solid #e5e5e5;">
                <a href="{FRONTEND_URL}/dashboard" style="display: inline-block; background: #1e40af; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    Open Dashboard
                </a>
            </div>
            
            <div style="background: #f9fafb; border-radius: 0 0 12px 12px; padding: 20px; text-align: center; border: 1px solid #e5e5e5; border-top: none;">
                <p style="color: #888; font-size: 12px; margin: 0;">
                    You're receiving this because you enabled Daily Digest.
                    <br>
                    <a href="{FRONTEND_URL}/settings/notifications" style="color: #1e40af;">Manage preferences</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    '''

async def send_daily_digests():
    """Send daily digest to all users with email_digest enabled"""
    print(f"[{datetime.now().isoformat()}] Starting daily digest job...")
    
    if not RESEND_API_KEY:
        print("ERROR: RESEND_API_KEY not configured")
        return
    
    resend.api_key = RESEND_API_KEY
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Find all users with email digest enabled
        prefs_cursor = db.notification_preferences.find({"email_digest": True})
        prefs_list = await prefs_cursor.to_list(length=1000)
        
        print(f"Found {len(prefs_list)} users with digest enabled")
        
        sent_count = 0
        failed_count = 0
        
        for pref in prefs_list:
            user_id = pref.get("user_id")
            
            # Get user info
            user = await db.users.find_one({"id": user_id})
            if not user or not user.get("email"):
                print(f"  Skipping user {user_id}: no email")
                continue
            
            # Get notifications from last 24 hours
            yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
            notifications = await db.notifications.find({
                "user_id": user_id,
                "created_at": {"$gte": yesterday.isoformat()}
            }).to_list(50)
            
            # Get unread count
            unread_count = await db.notifications.count_documents({
                "user_id": user_id,
                "read": False
            })
            
            user_name = user.get("full_name") or user.get("email", "").split("@")[0]
            stats = {"unread": unread_count}
            
            # Generate email
            html_content = generate_digest_html(user_name, notifications, stats)
            
            try:
                # Send email
                result = resend.Emails.send({
                    "from": SENDER_EMAIL,
                    "to": [user.get("email")],
                    "subject": f"☀️ Your Daily Sales Digest - {len(notifications)} notifications",
                    "html": html_content
                })
                
                print(f"  ✓ Sent to {user.get('email')}: {len(notifications)} notifications")
                sent_count += 1
                
                # Log the send
                await db.digest_logs.insert_one({
                    "user_id": user_id,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "notifications_count": len(notifications),
                    "email_id": str(result) if result else None
                })
                
            except Exception as e:
                print(f"  ✗ Failed for {user.get('email')}: {e}")
                failed_count += 1
        
        print(f"\n[{datetime.now().isoformat()}] Daily digest complete!")
        print(f"  Sent: {sent_count}")
        print(f"  Failed: {failed_count}")
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(send_daily_digests())
