# LeadGen Pro - Product Requirements Document

## Overview
LeadGen Pro is an internal, enterprise-grade AI-powered CRM and sales automation platform for team use. It serves as an all-in-one "sales command center" providing lead management, sales workflow automation, team collaboration, and AI-powered insights.

## Core Requirements

### User Management
- [x] JWT-based authentication (register, login)
- [x] Role-based access control (admin, manager, employee)
- [x] Onboarding wizard for new users
- [x] **Admin User Management** - Admins can create, edit, delete team members with:
  - Name, Email, Password
  - Role (employee/manager/admin)
  - Department
  - Phone/Contact info
  - Company
- [x] **Admin Lead Visibility** - Admins can see ALL leads regardless of who created them (FIXED Jan 9, 2026)

### Lead Management
- [x] Lead CRUD operations
- [x] Lead scoring (AI-powered)
- [x] Lead status and stage tracking
- [x] Bulk CSV import
- [x] Website scraping for contacts
- [x] Lead distribution by admins
- [x] Drag-and-drop Kanban pipeline
- [x] **Bulk Actions** (NEW - Jan 9, 2026):
  - Bulk assign leads to users
  - Bulk add leads to email sequences
  - Edit lead modal with expanded fields (mobile, address, notes)

### VoIP & Dialer System (Improved - v2)
- [x] Click-to-call via Twilio VoIP
- [x] **Physical Phone Dialer** - Fully redesigned, intuitive dial pad with:
  - Modern dark gradient design
  - T9 keypad with letter labels (ABC, DEF, etc.)
  - Clear phone number display with backspace
  - Call recording toggle (prominent red indicator)
  - **Recent calls list** - Quick redial from last 5 calls
  - **Call outcome logging** - Post-call modal to select outcome (Connected, Voicemail, No Answer, Busy, Wrong Number, Declined)
  - **Call notes** - Add notes to each call log
  - **Call status indicators** - Connecting, Ringing, Connected, Ended, Failed
  - Live call timer with animated status
- [x] **Post-Call Disposition Modal** (NEW - Jan 9, 2026):
  - 12 disposition options matching enterprise CRM standards
  - Notes field for call details
  - Automatic activity logging
  - Lead last_contacted timestamp update
- [x] **Twilio Integration** - Robust call handling with:
  - Proper webhook endpoints for call status events (`/api/voice/events`)
  - Recording completion callbacks (`/api/voice/recording-callback`)
  - Dial status tracking (`/api/voice/dial-status`)
  - Active call tracking in database
  - Automatic call log creation on completion
  - Recording URL storage for playback
  - Real-time call status polling
- [x] **Call Analytics** - Gong-like dashboard with:
  - Call logs with recordings
  - AI-powered transcription (OpenAI Whisper)
  - AI-powered call analysis
  - Coaching tips
  - Performance metrics
- [x] Call recording toggle
- [x] Email modal from lead records
- [x] Meeting scheduling from lead records
- [x] Activity history timeline per lead
- [x] Bulk email selection
- [x] **Screen Sharing** - VideoMeetingRoom component with WebRTC screen sharing

### Collaboration & Productivity
- [x] Team Calendar (fullcalendar.io integration)
- [x] **Calendly-like Booking System** - Public booking pages for each user
  - Date and time slot selection
  - Lead details form
  - Creates calendar event + lead record
  - Accessible via `/book/:userId`
  - **Email notifications** via Resend when bookings are made
- [x] Task management (Outreach-like)
- [x] **Enhanced Team Messaging** (Slack-like):
  - Public channels (#general, #sales, #leads)
  - Direct messaging to team members
  - @mentions with autocomplete
  - File attachment UI
  - Read receipts (delivered/read checkmarks)
  - Threaded conversations UI
  - Calendly-like availability viewing for team members
  - Copy booking link for any team member
- [x] Call lists for employees

### AI Features
- [x] **AI Sales Coach** (floating chatbot widget) with:
  - Chat tab for Q&A with quick questions
  - **Next Actions tab** - Proactive AI suggestions including:
    - Time-based suggestions (prime call time, email sweet spot)
    - Stats-based suggestions (leads needing follow-up, hot leads, tasks due)
    - Today's snapshot with key metrics
    - Motivational pro tips
  - Dark theme, positioned bottom-left
- [x] AI Copilot for onboarding (Getting Started Guide)
- [x] AI-powered lead insights
- [x] Call Analytics page (Gong-like dashboard)
- [x] **OpenAI Whisper Transcription** - Transcribe call recordings to text
- [x] **Gong-like AI Analysis** - Detailed call analysis including:
  - Overall call score (0-100)
  - Sentiment analysis
  - Talk ratio analysis
  - Question quality assessment
  - Customer signals detection
  - Next steps tracking
  - AI coaching insights

### Reporting
- [x] **Advanced Reporting Dashboard** (`/reports`):
  - Key metrics: Total Leads, Qualified, Won Deals, Conversion Rate, Avg Deal Size, Pipeline Value
  - Activity Trend chart (area chart)
  - Pipeline Distribution chart (pie chart)
  - Daily Performance chart (bar chart)
  - Lead Sources breakdown
  - Call Performance stats
  - Email Campaign performance table
  - Date range selector (7d, 30d, 90d)
  - Export button

## Implementation Status - January 10, 2026

### Completed This Session (Session 4)
1. **Two-Way Google Calendar Sync** (P0 - Previously BLOCKED)
   - Implemented full two-way sync (push LeadGen events to Google, pull Google events to LeadGen)
   - Added `/api/google/calendar/sync`, `/api/google/calendar/sync-status` endpoints
   - Added `/api/google/calendar/push-event/{event_id}` for individual event push
   - Settings page UI with sync controls and status display
   - User provided Google OAuth credentials: Successfully configured

2. **Smart Notifications System** (P1)
   - Hot Lead alerts (score ≥70, not contacted in 3+ days)
   - Stale Deal alerts (proposal/negotiation stage for 7+ days)
   - Meeting reminders (events starting within 1 hour)
   - Task Due Today alerts
   - Email Opened alerts
   - New Lead Assigned alerts
   - Auto-refreshes every 60 seconds, click to navigate to lead/task

3. **Notification Preferences Page** (P1) - NEW
   - `/settings/notifications` page with full customization
   - Toggle each alert type on/off
   - **Browser Push Notifications** - Get alerts even when tab is closed
   - Quiet Hours (pause notifications during set times)
   - Email Digest option (daily summary)
   - Enable All / Disable All quick actions

5. **Dashboard Notification Stats Widget** (P2) - NEW
   - Added `NotificationStatsWidget` component to Admin, Employee, and Main dashboards
   - Real-time stats grid: Hot Leads, Stale Deals, Tasks Due, Meetings
   - Recent notifications preview with click-to-navigate
   - Push notification enable banner
   - Quick refresh and mark-all-read buttons
   - Auto-refreshes every 60 seconds

6. **Daily Digest Email** (P2) - NEW
   - Beautiful HTML email template with morning greeting
   - Stats summary: Unread Alerts, Hot Leads, Tasks Due
   - Grouped notifications by type (Hot Leads, Stale Deals, Tasks, Meetings)
   - "Open Dashboard" CTA button
   - Endpoints: `/api/notifications/send-digest`, `/api/notifications/digest-preview`
   - Admin bulk send: `/api/notifications/send-digest-all`
   - Toggle in Settings with "Send Test Digest" and "Preview" buttons
   - Service Worker (`/public/sw.js`) for background notifications
   - VAPID key authentication for secure push
   - `/api/push/subscribe`, `/api/push/unsubscribe`, `/api/push/status` endpoints
   - Test notification feature to verify setup
   - Automatic cleanup of expired subscriptions
   - Click notification to navigate directly to relevant lead/task/calendar
   - **Auto-Push Integration**: Smart alerts automatically send push notifications when:
     - Hot leads need attention
     - Deals become stale
     - Meetings are starting soon
     - Tasks are due today
     - Leads open your emails
     - New leads are assigned to you

4. **Deal Value Field** (P2)
   - Added `deal_value` to Lead and LeadCreate models
   - Added Deal Value ($) input field in Edit Lead modal
   - Added Stage dropdown for easy pipeline management
   - Enables real data for Pipeline Forecasting dashboard

5. **Automatic Calendar Background Sync** (P2)
   - Enable/disable auto-sync toggle in Settings
   - `/api/google/calendar/auto-sync` endpoints for enable/disable/status
   - 15-minute sync interval setting

6. **Phone Dialer UI Optimization**
   - Made dialer more compact (max-w-md, max-h-[90vh])
   - Reduced padding and element sizes
   - Scrollable if content exceeds viewport

### Completed This Session
1. **Admin Lead Visibility Bug Fix** (P0)
   - Fixed critical bug where admins couldn't see leads uploaded by other admins
   - Updated `get_leads` endpoint to properly check `is_admin` before applying filters
   - Admins now see ALL leads in the system (55+ leads verified)

2. **Post-Call Disposition Modal**
   - Integrated `CallDispositionModal` with `PhoneDialer`
   - 12 enterprise-grade disposition options (No Answer, Left Voicemail, Gatekeeper, etc.)
   - Notes field for call details
   - Automatic activity logging and lead timestamp updates
   - Enhanced backend to create call_log from pending_call if webhook hasn't processed yet

3. **Bulk Lead Actions**
   - Bulk assign leads to users (`/api/leads/bulk-assign`)
   - Bulk add leads to email sequences (`/api/leads/bulk-sequence`)
   - Select Multiple button with toolbar showing selected count
   - Email Selected, Export Selected, Assign to User, Add to Sequence buttons

4. **Testing & Verification**
   - 15/15 backend tests passed
   - All frontend UI features verified working
   - Quick Call dialer visible and functional for all users

### Previous Session Completions
- Advanced Reporting Dashboard
- Enhanced Team Chat with @mentions and DMs
- AI Sales Coach Enhancement
- Calendly-like Scheduling System
- Gong-like Call Analytics Dashboard
- Google Sign-In Integration

### Session 2 Completions (Jan 9, 2026)
- **Delete Messages in Team Chat** - Author and admin can delete messages with trash icon
- **AI Call Coaching** - Comprehensive Gong-like coaching with:
  - Real-time coaching suggestions
  - Talk-to-listen ratio analysis
  - Sentiment analysis and alerts
  - Personalized improvement recommendations
  - Team performance insights
- **Google OAuth Setup Guide** - Created `/app/GOOGLE_OAUTH_SETUP.md` for two-way calendar sync
- **Waveform Audio Player** - Enhanced call recording playback:
  - Visual waveform bars with animated playhead
  - Play/Pause, Skip ±10s, Playback speed (1x-2x)
  - Volume control and time display
  - **AI Coaching Insight Markers** on timeline (color-coded dots)
  - Click markers to jump to coaching moments
  - Active insight display with suggestions
- **Web Audio API Integration** (NEW) - Real waveform visualization:
  - Analyzes actual audio frequency data
  - **Speaker Detection Colors**: Blue (rep), Green (customer), Gray (silence)
  - Shows real audio peaks and valleys
- **Email Tracking & Analytics** (NEW):
  - Tracking pixel for email opens (`/api/email/tracking/pixel/{email_id}.gif`)
  - Link click tracking with redirect
  - Email Analytics Dashboard (`/email-analytics`)
  - Open rate, click rate, reply rate metrics
  - Daily trend charts and email funnel visualization
- **Email Sequences (Drip Campaigns)** (NEW):
  - Create multi-step email sequences
  - Enroll/unenroll leads from sequences
  - Auto-pause on reply or meeting booked
  - Sequence performance tracking
- **Pipeline Revenue Forecasting** (NEW):
  - AI-powered deal probability predictions
  - Weighted pipeline calculations
  - Monthly and quarterly forecasts
  - Stage distribution charts
  - Deal Analysis with AI recommendations
  - At-risk deals identification
- **Command Palette (Cmd+K)** (NEW):
  - Quick search across leads by name, company, email
  - Fast navigation to any page
  - Quick actions: New Lead, New Task, Quick Call, Schedule Meeting
  - Keyboard shortcuts for power users
  - Recent searches saved locally
  - Pro tip hints for efficiency

### Backend Endpoints (New - Session 3 - Jan 10, 2026)
- `/api/google/calendar/sync` (POST) - Full two-way calendar sync
- `/api/google/calendar/sync-status` (GET) - Detailed sync status with event counts
- `/api/google/calendar/events/{event_id}` (PUT) - Update event in both calendars
- `/api/google/calendar/events/{event_id}` (DELETE) - Delete event from both calendars
- `/api/google/calendar/push-event/{event_id}` (POST) - Push single event to Google

### Backend Endpoints (New - Session 2)
- `/api/leads/bulk-assign` - Assign multiple leads to a user
- `/api/leads/bulk-sequence` - Add multiple leads to a sequence
- `/api/calls/{call_id}/disposition` - Update call disposition with notes
- `/api/calls/dispositions` - Get available disposition options
- `/api/chat/messages/{message_id}` (DELETE) - Delete a chat message
- `/api/calls/{call_id}/coaching` (POST) - Get comprehensive AI coaching for a call
- `/api/calls/coaching/team-insights` (GET) - Get aggregated team coaching insights
- `/api/email/tracking/pixel/{email_id}.gif` (GET) - Email open tracking pixel
- `/api/email/tracking/click/{email_id}/{link_id}` (GET) - Link click tracking
- `/api/email/tracking/stats` (GET) - Email tracking statistics
- `/api/email/tracking/{email_id}` (GET) - Detailed tracking for specific email
- `/api/sequences` (GET, POST) - List and create email sequences
- `/api/sequences/{sequence_id}` (GET, PUT, DELETE) - Manage specific sequence
- `/api/sequences/{sequence_id}/enroll` (POST) - Enroll leads in sequence
- `/api/sequences/{sequence_id}/unenroll/{lead_id}` (POST) - Unenroll lead
- `/api/forecasting/pipeline` (GET) - Pipeline forecast with weighted probabilities
- `/api/forecasting/analyze-deal/{lead_id}` (POST) - AI deal analysis

### Backend Endpoints (Existing)
- `/api/booking/{user_id}` - Get user info for booking
- `/api/booking/{user_id}/slots` - Get available slots
- `/api/booking/{user_id}/book` - Create booking
- `/api/admin/users` - CRUD for user management
- `/api/team-members` - List team members
- `/api/stats` - Dashboard statistics
- `/api/calls/stats` - Call statistics
- `/api/email/campaigns` - Email campaign data

### Frontend Routes
- `/book/:userId` - Public booking page
- `/admin/users` - Admin user management
- `/reports` - Advanced Reporting Dashboard
- `/meetings` - Meetings management with VideoMeetingRoom

## Blocked Items
- **Email Notifications (Resend)** - In sandbox mode, can only send to verified emails. User needs to verify domain in Resend dashboard.

## Recently Unblocked (Jan 10, 2026)
- **Two-Way Google Calendar Sync** - ✅ IMPLEMENTED! User provided Google OAuth credentials.
  - Full two-way sync (push LeadGen events to Google, pull Google events to LeadGen)
  - Sync status tracking with event counts
  - Individual event push/pull options
  - Auto-refresh of expired OAuth tokens
  - Settings page UI with sync controls
  - **Automatic Background Sync** - 15-minute interval option added

## Paused Items
- **Google Drive Content Hub** - OAuth flow paused by user request

## Future/Backlog (P2)
- [ ] Connect AI Email "Generate" button to LLM
- [ ] CRM Integrations (HubSpot/Salesforce placeholders)
- [ ] Continue backend refactoring (Phase 9+: Public API, misc endpoints)

## Backend Refactoring Progress (Jan 10, 2026)
**COMPLETED - Phase 1 through Phase 8**
- Created `/app/backend/core/` module:
  - `config.py` - Environment variables
  - `database.py` - MongoDB connection
  - `security.py` - JWT auth, User models, auth helpers
- Created `/app/backend/routes/` module (12 files):
  - `notifications.py` - Notification system (~700 lines)
  - `push.py` - Web push (~150 lines)
  - `auth.py` - Authentication (~240 lines)
  - `leads.py` - Lead management (~350 lines)
  - `calendar.py` - Calendar/appointments (~256 lines)
  - `calls.py` - Voice/Twilio (~713 lines)
  - `chat.py` - Team chat, DMs, reactions (~370 lines)
  - `booking.py` - Public booking (~320 lines)
  - `admin.py` - Admin management (~457 lines) **NEW Phase 7**
  - `email.py` - Email automation, sequences, tracking (~750 lines) **NEW Phase 8**
  - `forecasting.py` - Pipeline forecasting, deal analysis (~170 lines) **NEW Phase 8**
  - `google.py` - Google Drive/Calendar OAuth, sync (~730 lines) **NEW Phase 8**
- Created `/app/backend/send_daily_digest.py` - Daily digest cron job
- **Total Impact**: Reduced server.py from ~9,100 to ~3,746 lines (~5,354 lines extracted, **59% reduction**)

**See**: `/app/backend/REFACTORING.md` for full plan and next steps

## Technical Architecture

### Tech Stack
- **Frontend**: React, Tailwind CSS, react-router-dom, lucide-react, recharts, framer-motion
- **Backend**: FastAPI, MongoDB (pymongo), JWT auth
- **Integrations**: Twilio (VoIP), Emergent LLM Key (AI features, Whisper STT), Resend (email notifications)

### Key Files
- `/app/backend/server.py` - Main API server (~8,250 lines, refactoring in progress)
- `/app/backend/routes/notifications.py` - Notification endpoints (modular)
- `/app/backend/routes/push.py` - Push notification endpoints (modular)
- `/app/backend/core/security.py` - Auth utilities (modular)
- `/app/backend/send_daily_digest.py` - Cron job for daily digest emails
- `/app/frontend/src/pages/AdvancedReportingPage.js` - Reporting dashboard
- `/app/frontend/src/components/TeamChat.js` - Enhanced team messaging
- `/app/frontend/src/components/AIAssistant.js` - AI Sales Coach with Next Actions
- `/app/frontend/src/components/VideoMeetingRoom.js` - Screen sharing component
- `/app/frontend/src/pages/BookingPage.js` - Public booking UI
- `/app/frontend/src/pages/AdminUsersPage.js` - Admin user management
- `/app/frontend/src/components/PhoneDialer.js` - Physical dialer

## Test Credentials
- Admin: `admin@test.com` / `admin123`

## 3rd Party Integrations
- **Twilio Voice**: Implemented and verified
- **OpenAI Whisper**: Implemented via `emergentintegrations`
- **Resend**: Implemented but blocked by sandbox mode
- **Google Drive**: Partially implemented, paused
- **Google Calendar**: ✅ Two-way sync implemented (Jan 10, 2026)

## Deployment Configuration

### Security Settings (Updated)
- **JWT_SECRET**: Secure 64-character token generated
- **CORS_ORIGINS**: Configured for `leadgenpro2.com` domain
- **API Keys**: User-generated keys for external integrations

### Public API System (NEW)
The platform now includes a full public API for external integrations:

**Base URL**: `/api/public`
**Authentication**: API Key via `X-API-Key` header

**Available Endpoints**:
- `GET /public/health` - Health check (no auth)
- `GET /public/docs` - API documentation
- **Leads**: GET, POST, PUT, DELETE `/public/leads`
- **Appointments**: GET, POST, DELETE `/public/appointments`
- **Calls**: GET, POST `/public/calls`
- **Tasks**: GET, POST `/public/tasks`
- **Activities**: GET, POST `/public/activities`
- **Webhooks**: Subscribe to events (lead.created, call.completed, etc.)

**Permissions**: read, write, delete, admin

### Settings Page (NEW)
- Profile management (name, phone, company, department)
- API Key management (create, view, delete)
- Integration status overview