# LeadGen Pro Backend Refactoring Plan

## Current State
- `server.py`: ~7,403 lines (reduced from ~9,100)
- Notifications, Push, Auth, Leads, and Calendar endpoints moved to modular routes
- Core configuration extracted to separate modules

## Refactoring Progress

### Phase 1 (Completed ✅) - ~850 lines extracted
- [x] Create `core/config.py` - Environment variables
- [x] Create `core/database.py` - MongoDB connection
- [x] Create `core/security.py` - JWT auth, User model, Token, auth helpers
- [x] Create `routes/notifications.py` - All notification endpoints
- [x] Create `routes/push.py` - Web push notification endpoints
- [x] Create `send_daily_digest.py` - Cron script for daily digest
- [x] Set up crontab for daily digest (8 AM UTC)

### Phase 2 (Completed ✅) - ~240 lines extracted
- [x] Create `routes/auth.py` - All authentication endpoints
  - /auth/register, /auth/login, /auth/me, /auth/profile
  - /auth/onboarding, /auth/google, /auth/logout, /auth/check-admin

### Phase 3 (Completed ✅) - ~350 lines extracted
- [x] Create `routes/leads.py` - All lead management endpoints
  - GET/POST/PUT/DELETE /leads (CRUD)
  - /leads/{id}/stage, /leads/bulk-import, /leads/bulk-assign
  - /leads/bulk-sequence, /leads/scrape

### Phase 4 (Completed ✅) - ~256 lines extracted
- [x] Create `routes/calendar.py` - All calendar and appointment endpoints
  - GET/POST /appointments
  - GET/POST/DELETE /calendar/events
  - /calendar/events/with-meet, /calendar/events/{id}/add-meet
  - /calendar/export/ics/{id}, /calendar/export/google-url/{id}
  - /calendar/sync-status

**Total Progress:** Server.py reduced from ~9,100 to ~7,403 lines (~1,697 lines extracted)

### Phase 5 (Next Priority)
- [ ] Extract call/voice endpoints to `routes/calls.py`
  - Twilio integration, call logs, call analytics
  - Voice token, call dispositions

### Phase 6
- [ ] Extract booking endpoints to `routes/booking.py`
- [ ] Extract chat endpoints to `routes/chat.py`
- [ ] Extract admin endpoints to `routes/admin.py`

### Phase 7
- [ ] Extract AI services to `services/ai.py`
- [ ] Extract email services to `services/email.py`
- [ ] Clean up server.py to be minimal entry point

## Current Architecture
```
/app/backend/
├── server.py              # Main app (~7,400 lines, refactoring in progress)
├── core/
│   ├── config.py          # ✅ Environment variables
│   ├── database.py        # ✅ MongoDB setup
│   └── security.py        # ✅ JWT, User model, auth helpers
├── routes/
│   ├── __init__.py        # ✅ Router exports
│   ├── auth.py            # ✅ Authentication endpoints
│   ├── leads.py           # ✅ Lead CRUD, bulk ops, scraping
│   ├── notifications.py   # ✅ Smart notifications, preferences, digest
│   ├── push.py            # ✅ Web push notifications
│   └── calendar.py        # ✅ Calendar events, appointments, Meet
├── send_daily_digest.py   # ✅ Cron script
└── requirements.txt
```

## Cron Job Setup
```bash
# Daily digest emails sent at 8 AM UTC
0 8 * * * cd /app/backend && /root/.venv/bin/python send_daily_digest.py >> /var/log/digest_cron.log 2>&1
```

## Notes
- The main GET /notifications endpoint remains in server.py (includes admin error handling)
- Google Calendar sync endpoints remain in server.py (complex dependencies)
- Old deprecated route files: leads_routes.py, auth_routes.py, calendar.py (old)
- Estimated remaining work: 2-3 more sessions for full refactor
