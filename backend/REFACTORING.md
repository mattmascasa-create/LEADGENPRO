# LeadGen Pro Backend Refactoring Plan

## Current State
- `server.py`: ~9,100 lines (monolithic)
- All endpoints, models, and business logic in one file

## Target Architecture
```
/app/backend/
├── server.py              # Main app entry, minimal (~200 lines)
├── core/
│   ├── __init__.py
│   ├── config.py          # Environment variables ✅ DONE
│   ├── database.py        # MongoDB setup ✅ DONE
│   └── security.py        # JWT, password hashing
├── models/
│   ├── __init__.py
│   ├── user.py            # User, UserCreate, UserLogin models
│   ├── lead.py            # Lead, LeadCreate models
│   ├── notification.py    # SmartNotification, NotificationPreferences
│   └── ...
├── routes/
│   ├── __init__.py        ✅ UPDATED
│   ├── auth.py            # /auth/* endpoints
│   ├── leads.py           # /leads/* endpoints
│   ├── notifications.py   # ✅ DONE - Smart notifications, push, digest
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
└── utils/
    ├── __init__.py
    └── helpers.py         # Common utility functions
```

## Refactoring Priority

### Phase 1 (Completed)
- [x] Create `core/config.py` - Environment variables
- [x] Create `core/database.py` - MongoDB connection
- [x] Create `routes/notifications.py` - Notification logic extracted

### Phase 2 (Next)
- [ ] Extract auth endpoints to `routes/auth.py`
- [ ] Extract leads endpoints to `routes/leads.py`
- [ ] Create `core/security.py` for auth utilities

### Phase 3
- [ ] Extract calendar endpoints to `routes/calendar.py`
- [ ] Extract call/voice endpoints to `routes/calls.py`
- [ ] Extract chat endpoints to `routes/chat.py`

### Phase 4
- [ ] Extract admin endpoints to `routes/admin.py`
- [ ] Extract AI services to `services/ai.py`
- [ ] Clean up server.py to import from modules

## Benefits
1. **Maintainability**: Smaller, focused files
2. **Testing**: Easier to unit test individual modules
3. **Collaboration**: Multiple developers can work on different files
4. **Performance**: Faster code navigation and IDE support
5. **Debugging**: Easier to locate and fix issues

## Migration Strategy
- Gradual migration (keep server.py working during transition)
- Extract one module at a time
- Test thoroughly after each extraction
- Update imports in server.py to use new modules

## Files Created This Session
1. `/app/backend/core/config.py` - All environment variables
2. `/app/backend/core/database.py` - MongoDB connection
3. `/app/backend/routes/notifications.py` - Notification models and helpers

## Notes
- The full refactor is estimated at 2-3 sessions
- Server.py remains functional during incremental refactoring
- New features should be added to the new module structure when possible
