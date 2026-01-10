# LeadGen Pro Backend Refactoring Plan

## Current State
- `server.py`: ~8,010 lines (reduced from ~9,100)
- Notifications, Push, Auth endpoints moved to modular routes
- Core configuration extracted to separate modules

## Target Architecture
```
/app/backend/
├── server.py              # Main app entry, minimal (~200 lines) [IN PROGRESS]
├── core/
│   ├── __init__.py
│   ├── config.py          # Environment variables ✅ DONE
│   ├── database.py        # MongoDB setup ✅ DONE
│   └── security.py        # JWT, password hashing, User model ✅ DONE
├── models/
│   ├── __init__.py
│   ├── user.py            # User, UserCreate, UserLogin models
│   ├── lead.py            # Lead, LeadCreate models
│   ├── notification.py    # SmartNotification, NotificationPreferences
│   └── ...
├── routes/
│   ├── __init__.py        ✅ UPDATED
│   ├── auth.py            # ✅ DONE - /auth/* endpoints
│   ├── leads.py           # /leads/* endpoints
│   ├── notifications.py   # ✅ DONE - Smart notifications, preferences, digest
│   ├── push.py            # ✅ DONE - Web push notifications
│   ├── calendar.py        # Calendar & Google Calendar sync
│   ├── calls.py           # Twilio voice, call logs, analytics
│   ├── chat.py            # Team chat endpoints
│   ├── admin.py           # Admin-only endpoints
│   └── ...
├── services/
│   ├── __init__.py
│   ├── ai.py              # AI insights, call coaching
│   ├── email.py           # Resend email service
│   ├── push.py            # Web push notifications
│   └── twilio.py          # Twilio integration
├── utils/
│   ├── __init__.py
│   └── helpers.py         # Common utility functions
├── send_daily_digest.py   # ✅ DONE - Cron script for daily digest
└── requirements.txt
```

## Refactoring Progress

### Phase 1 (Completed ✅)
- [x] Create `core/config.py` - Environment variables
- [x] Create `core/database.py` - MongoDB connection
- [x] Create `core/security.py` - JWT auth, User model, Token, auth helpers
- [x] Create `routes/notifications.py` - All notification endpoints extracted
- [x] Create `routes/push.py` - Web push notification endpoints extracted
- [x] Create `send_daily_digest.py` - Cron script for automated daily digest emails
- [x] Set up crontab for daily digest (8 AM UTC)

**Impact:** Removed ~850 lines from server.py

### Phase 2 (Completed ✅)
- [x] Create `routes/auth.py` - All authentication endpoints extracted
  - /auth/register
  - /auth/login
  - /auth/me
  - /auth/profile
  - /auth/onboarding
  - /auth/google (Emergent OAuth)
  - /auth/me/google-link-status
  - /auth/logout
  - /auth/check-admin
- [x] Update `core/security.py` with UserCreate, UserLogin, Token models

**Impact:** Removed ~240 additional lines from server.py

**Total Progress:** Server.py reduced from ~9,100 to ~8,010 lines (~1,090 lines extracted)

### Phase 3 (Next Priority)
- [ ] Extract leads endpoints to `routes/leads.py`
  - /leads CRUD
  - /leads/bulk-import
  - /leads/bulk-assign
  - /leads/bulk-sequence
  - /leads/scrape
- [ ] Extract appointments endpoints

### Phase 4
- [ ] Extract calendar endpoints to `routes/calendar.py`
- [ ] Extract call/voice endpoints to `routes/calls.py`
- [ ] Extract chat endpoints to `routes/chat.py`

### Phase 5
- [ ] Extract admin endpoints to `routes/admin.py`
- [ ] Extract AI services to `services/ai.py`
- [ ] Clean up server.py to be minimal entry point

## Benefits Achieved
1. **Maintainability**: Auth and Notification logic now in focused, testable modules
2. **Separation of Concerns**: Each route file handles one domain
3. **Automated Operations**: Daily digest runs automatically via cron
4. **Testing**: Easier to unit test individual modules
5. **Scalability**: New features can be added to appropriate modules

## Migration Strategy
- Gradual migration (keep server.py working during transition)
- Extract one module at a time
- Test thoroughly after each extraction
- Update imports in server.py to use new modules

## Files Created/Modified
1. `/app/backend/core/config.py` - All environment variables
2. `/app/backend/core/database.py` - MongoDB connection
3. `/app/backend/core/security.py` - Auth utilities, User models
4. `/app/backend/routes/notifications.py` - Complete notification system
5. `/app/backend/routes/push.py` - Web push endpoints
6. `/app/backend/routes/auth.py` - Authentication endpoints (NEW)
7. `/app/backend/routes/__init__.py` - Router exports
8. `/app/backend/send_daily_digest.py` - Cron script

## Cron Job Setup
```bash
# Daily digest emails sent at 8 AM UTC
0 8 * * * cd /app/backend && /root/.venv/bin/python send_daily_digest.py >> /var/log/digest_cron.log 2>&1
```

## Notes
- The main GET /notifications endpoint remains in server.py (includes admin error handling)
- All other notification and auth endpoints are in modular routes
- Server.py remains functional during incremental refactoring
- New features should be added to the new module structure when possible
- Estimated remaining work: 2-3 more sessions for full refactor
