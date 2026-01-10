"""
Routes module for LeadGen Pro backend
"""
from routes import notifications
from routes import push
from routes import auth
from routes import leads
from routes import calendar
from routes import calls
from routes import chat
from routes import booking
from routes import admin
from routes import email
from routes import forecasting
from routes import google
from routes import tasks
from routes import meetings
from routes import public_api

# Export routers
notifications_router = notifications.router
push_router = push.router
auth_router = auth.router
leads_router = leads.router
calendar_router = calendar.router
calls_router = calls.router
chat_router = chat.router
booking_router = booking.router
admin_router = admin.router
email_router = email.router
forecasting_router = forecasting.router
google_router = google.router
tasks_router = tasks.router
meetings_router = meetings.router
public_api_router = public_api.router

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

# Export chat utilities
from routes.chat import (
    Channel,
    ChatMessage,
    ChatMessageCreate,
    UserStatus,
    UpdateStatusRequest,
    STATUS_PRESETS
)

# Export booking utilities
from routes.booking import (
    BookingRequest,
    AvailabilitySlot,
    MeetingType
)

# Export admin utilities
from routes.admin import (
    AdminUserCreate,
    AdminUserUpdate,
    DailyGoals
)

# Export email utilities
from routes.email import (
    EmailTemplate,
    EmailCampaign,
    ScheduledEmail,
    EmailSequence,
    SequenceStep,
    SequenceEnrollment,
    EmailGenerateRequest,
    BulkEmailRequest
)

# Export forecasting utilities
from routes.forecasting import (
    DealForecast
)

# Export google utilities
from routes.google import (
    CalendarSyncRequest,
    get_google_credentials,
    get_drive_service,
    get_calendar_service,
    GOOGLE_SCOPES
)

# Export task utilities
from routes.tasks import (
    Task,
    TaskCreate,
    TaskUpdate
)

# Export meetings utilities
from routes.meetings import (
    MeetingType as MeetingTypeModel,
    MeetingTypeCreate,
    AvailabilityRule,
    UserStatusUpdate
)

# Export public API utilities
from routes.public_api import (
    APIKey,
    CreateAPIKeyRequest,
    PublicLeadCreate,
    WebhookSubscription,
    get_api_key_user
)

__all__ = [
    'notifications_router',
    'push_router',
    'auth_router',
    'leads_router',
    'calendar_router',
    'calls_router',
    'chat_router',
    'booking_router',
    'admin_router',
    'email_router',
    'forecasting_router',
    'google_router',
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
    'format_phone_e164',
    'Channel',
    'ChatMessage',
    'ChatMessageCreate',
    'UserStatus',
    'UpdateStatusRequest',
    'STATUS_PRESETS',
    'BookingRequest',
    'AvailabilitySlot',
    'MeetingType',
    'AdminUserCreate',
    'AdminUserUpdate',
    'DailyGoals',
    'EmailTemplate',
    'EmailCampaign',
    'ScheduledEmail',
    'EmailSequence',
    'SequenceStep',
    'SequenceEnrollment',
    'EmailGenerateRequest',
    'BulkEmailRequest',
    'DealForecast',
    'CalendarSyncRequest',
    'get_google_credentials',
    'get_drive_service',
    'get_calendar_service',
    'GOOGLE_SCOPES'
]
