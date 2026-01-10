"""
Routes module for LeadGen Pro backend
"""
from routes import notifications
from routes import push
from routes import auth

# Export routers
notifications_router = notifications.router
push_router = push.router
auth_router = auth.router

# Export notification utilities for use in other modules
from routes.notifications import (
    NotificationType,
    SmartNotification,
    NotificationPreferences,
    send_push_to_user,
    should_send_notification,
    create_lead_assigned_notification
)

__all__ = [
    'notifications_router',
    'push_router',
    'auth_router',
    'NotificationType',
    'SmartNotification',
    'NotificationPreferences',
    'send_push_to_user',
    'should_send_notification',
    'create_lead_assigned_notification'
]
