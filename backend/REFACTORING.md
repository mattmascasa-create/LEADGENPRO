# LeadGen Pro Backend Refactoring Plan

## Current State
- `server.py`: ~6,690 lines (reduced from ~9,100)
- Notifications, Push, Auth, Leads, Calendar, and Calls endpoints moved to modular routes
- Core configuration extracted to separate modules

## Refactoring Progress

### Phase 1 (Completed ✅) - ~850 lines extracted
- [x] Create `core/config.py`, `core/database.py`, `core/security.py`
- [x] Create `routes/notifications.py`, `routes/push.py`
- [x] Create `send_daily_digest.py` + crontab

### Phase 2 (Completed ✅) - ~240 lines extracted
- [x] Create `routes/auth.py` - All authentication endpoints

### Phase 3 (Completed ✅) - ~350 lines extracted
- [x] Create `routes/leads.py` - Lead CRUD, bulk ops, scraping

### Phase 4 (Completed ✅) - ~256 lines extracted
- [x] Create `routes/calendar.py` - Calendar events, appointments, Meet

### Phase 5 (Completed ✅) - ~713 lines extracted
- [x] Create `routes/calls.py` - All voice/call endpoints
  - /calls/dispositions, /calls/{id}/disposition
  - /voice/token, /voice/call, /voice/connect/*
  - /voice/dial-status, /voice/call-complete/*
  - /voice/hangup, /voice/events, /voice/recording-callback
  - /calls/log, /calls/logs, /calls/stats

**Note**: AI-powered call features (analysis, transcribe, coaching) remain in server.py due to LLM dependencies.

**Total Progress:** Server.py reduced from ~9,100 to ~6,690 lines (~2,410 lines extracted, 26.5% reduction)

### Phase 6 (Next Priority)
- [ ] Extract booking endpoints to `routes/booking.py`
- [ ] Extract chat endpoints to `routes/chat.py`

### Phase 7
- [ ] Extract admin endpoints to `routes/admin.py`
- [ ] Extract AI services to `services/ai.py`
- [ ] Clean up server.py to be minimal entry point

## Current Architecture
```
/app/backend/
├── server.py              # Main app (~6,690 lines)
├── core/
│   ├── config.py          # ✅ Environment variables
│   ├── database.py        # ✅ MongoDB setup
│   └── security.py        # ✅ JWT, User model
├── routes/
│   ├── auth.py            # ✅ Authentication
│   ├── leads.py           # ✅ Lead management
│   ├── notifications.py   # ✅ Smart notifications
│   ├── push.py            # ✅ Web push
│   ├── calendar.py        # ✅ Calendar/appointments
│   └── calls.py           # ✅ Voice/Twilio (NEW)
├── send_daily_digest.py   # ✅ Cron script
└── requirements.txt
```

## Cron Job
```bash
0 8 * * * cd /app/backend && /root/.venv/bin/python send_daily_digest.py >> /var/log/digest_cron.log 2>&1
```
