"""
Routes module for LeadGen Pro backend
"""
from . import notifications
from . import push

# Export routers
notifications_router = notifications.router
push_router = push.router

# Export notification utilities for use in other modules
from .notifications import (
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
    'NotificationType',
    'SmartNotification',
    'NotificationPreferences',
    'send_push_to_user',
    'should_send_notification',
    'create_lead_assigned_notification'
]
