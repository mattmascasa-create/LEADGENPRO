"""
LeadGen Pro - Routes Package
============================

This package contains modular route handlers. The main server.py 
is being gradually refactored to use these modules.

CURRENT STRUCTURE:
- auth_routes.py      - Authentication (login, register, Google OAuth)  [READY]
- leads_routes.py     - Lead management (CRUD, bulk import)             [READY]
- database.py         - Database configuration

PLANNED MODULES (to be extracted from server.py):
- appointments.py     - Appointment/booking management
- chat.py            - Team chat and messaging
- voice.py           - Twilio voice/call handling
- analytics.py       - Call analytics and reporting
- scheduling.py      - Calendly-like scheduling
- admin.py           - Admin operations
- tasks.py           - Task management
- errors.py          - Error handling system
- notifications.py   - Notifications system
- calendar.py        - Calendar events and Google Calendar
- sequences.py       - Email sequences
- templates.py       - Email templates

HOW TO USE:
-----------
In server.py, import and include routers:

from routes.auth_routes import router as auth_router
from routes.leads_routes import router as leads_router
app.include_router(auth_router, prefix="/api")
app.include_router(leads_router, prefix="/api")

Note: The modular routes are self-contained with their own 
database connections and authentication handling.
"""

# Import routers for easy access
try:
    from .auth_routes import router as auth_router
    from .leads_routes import router as leads_router
except ImportError as e:
    print(f"Warning: Could not import routers: {e}")
    auth_router = None
    leads_router = None

__all__ = ['auth_router', 'leads_router']