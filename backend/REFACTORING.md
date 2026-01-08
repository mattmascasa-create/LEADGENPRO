# LeadGen Pro - Backend Refactoring Guide

## Overview

The `server.py` file has grown to **6,765 lines** with **144 endpoints**. This document outlines the modular structure being implemented to improve maintainability.

## Current Status

### ✅ Completed
- `/app/backend/routes/auth_routes.py` - Authentication (ready to use)
- `/app/backend/routes/leads_routes.py` - Lead management (ready to use)
- `/app/backend/models/schemas.py` - All Pydantic models
- Removed dead code: `/app/frontend/src/components/TeamChat.js`

### 🔄 In Progress
- Main server.py still contains all endpoints (working)
- Modular routes are ready but not yet integrated to avoid breaking changes

## Target Structure

```
/app/backend/
├── server.py                 # Main app entry point (minimal)
├── core/
│   ├── __init__.py          # Database, security, shared utilities
│   └── config.py            # Environment configuration
├── models/
│   ├── __init__.py
│   └── schemas.py           # All Pydantic models ✅
├── routes/
│   ├── __init__.py          # Router registry ✅
│   ├── auth_routes.py       # Authentication ✅
│   ├── leads_routes.py      # Lead management ✅
│   ├── appointments.py      # Appointments & booking
│   ├── chat.py              # Team chat
│   ├── voice.py             # Twilio voice/calls
│   ├── analytics.py         # Call analytics
│   ├── scheduling.py        # Calendly-like scheduling
│   ├── admin.py             # Admin operations
│   ├── tasks.py             # Task management
│   ├── errors.py            # Error handling system
│   ├── notifications.py     # Notifications
│   ├── calendar.py          # Calendar events
│   ├── sequences.py         # Email sequences
│   └── templates.py         # Email templates
├── services/
│   ├── __init__.py
│   ├── email_service.py     # Resend email
│   ├── twilio_service.py    # Twilio voice/SMS
│   ├── ai_service.py        # LLM integrations
│   └── google_service.py    # Google APIs
└── utils/
    ├── __init__.py
    └── helpers.py           # Shared helper functions
```

## How to Migrate an Endpoint

1. **Create the route file** in `/app/backend/routes/`
2. **Copy relevant endpoints** from server.py
3. **Update imports** to be self-contained
4. **Test thoroughly** before removing from server.py
5. **Include router** in server.py:
   ```python
   from routes.auth_routes import router as auth_router
   app.include_router(auth_router, prefix="/api")
   ```

## Endpoint Groups (for extraction)

### Authentication (~220 lines)
- POST /auth/register
- POST /auth/login
- GET /auth/me
- PUT /auth/profile
- PUT /auth/onboarding
- POST /auth/google
- GET /auth/me/google-link-status
- POST /auth/logout

### Leads (~350 lines)
- GET /leads
- POST /leads
- GET /leads/{lead_id}
- PUT /leads/{lead_id}
- DELETE /leads/{lead_id}
- POST /leads/{lead_id}/stage
- POST /leads/bulk-import
- POST /leads/scrape

### Voice/Twilio (~600 lines)
- POST /voice/token
- POST /voice/call
- POST /voice/connect/{call_id}
- POST /voice/call-complete/{call_id}
- ... and more

### Chat (~300 lines)
- GET /chat/channels
- POST /chat/channels
- GET /chat/messages/{channel_id}
- POST /chat/messages
- POST /chat/messages/{message_id}/reactions
- POST /chat/messages/{message_id}/thread

### Scheduling (~400 lines)
- GET /meeting-types
- POST /meeting-types
- PUT /meeting-types/{id}
- DELETE /meeting-types/{id}
- GET /availability
- PUT /availability
- GET /booking/{user_id}/meeting-types
- GET /booking/{user_id}/slots/{meeting_type_id}
- POST /booking/{user_id}/book

### Call Analytics (~300 lines)
- GET /call-analytics
- GET /call-recordings
- POST /call-recordings/{call_id}/analyze
- GET /call-analytics/leaderboard

## Testing After Refactoring

After each module extraction:
1. Restart backend: `sudo supervisorctl restart backend`
2. Run API tests: `curl -X POST $API_URL/api/auth/login ...`
3. Check frontend functionality
4. Use testing subagent for comprehensive tests

## Notes

- Each route file should be self-contained with its own imports
- Avoid circular imports by not sharing db connections across files
- Keep models in the central schemas.py file
- Use environment variables for all configuration
