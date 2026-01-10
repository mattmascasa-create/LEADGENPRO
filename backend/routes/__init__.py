"""
Routes module for LeadGen Pro backend
"""
from routes import notifications
from routes import push
from routes import auth
from routes import leads
from routes import calendar
from routes import calls

# Export routers
notifications_router = notifications.router
push_router = push.router
auth_router = auth.router
leads_router = leads.router
calendar_router = calendar.router
calls_router = calls.router

# Export notification utilities
from routes.notifications import (
    NotificationType,
    SmartNotification,
    NotificationPreferences,
    send_push_to_user,
    should_send_notification,
    create_lead_assigned_notification
)

# Export lead utilities
from routes.leads import (
    Lead,
    LeadCreate,
    Activity,
    calculate_lead_score
)

# Export calendar utilities
from routes.calendar import (
    Appointment,
    AppointmentCreate,
    CalendarEvent,
    CalendarEventCreate,
    generate_google_meet_link
)

# Export call utilities
from routes.calls import (
    CallLog,
    CallLogCreate,
    CallOutcome,
    CALL_DISPOSITIONS,
    format_phone_e164
)

__all__ = [
    'notifications_router',
    'push_router',
    'auth_router',
    'leads_router',
    'calendar_router',
    'calls_router',
    'NotificationType',
    'SmartNotification',
    'NotificationPreferences',
    'send_push_to_user',
    'should_send_notification',
    'create_lead_assigned_notification',
    'Lead',
    'LeadCreate',
    'Activity',
    'calculate_lead_score',
    'Appointment',
    'AppointmentCreate',
    'CalendarEvent',
    'CalendarEventCreate',
    'generate_google_meet_link',
    'CallLog',
    'CallLogCreate',
    'CallOutcome',
    'CALL_DISPOSITIONS',
    'format_phone_e164'
]
