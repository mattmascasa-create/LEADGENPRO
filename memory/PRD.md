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

## Implementation Status - January 9, 2026

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

### Backend Endpoints (New)
- `/api/leads/bulk-assign` - Assign multiple leads to a user
- `/api/leads/bulk-sequence` - Add multiple leads to a sequence
- `/api/calls/{call_id}/disposition` - Update call disposition with notes
- `/api/calls/dispositions` - Get available disposition options
- `/api/chat/messages/{message_id}` (DELETE) - Delete a chat message
- `/api/calls/{call_id}/coaching` (POST) - Get comprehensive AI coaching for a call
- `/api/calls/coaching/team-insights` (GET) - Get aggregated team coaching insights

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
- **Two-Way Google Calendar Sync** - Blocked on user providing Google OAuth credentials. Setup guide at `/app/GOOGLE_OAUTH_SETUP.md`

## Paused Items
- **Google Drive Content Hub** - OAuth flow paused by user request

## Future/Backlog (P2)
- [ ] Connect AI Email "Generate" button to LLM
- [ ] CRM Integrations (HubSpot/Salesforce placeholders)
- [ ] Backend refactoring (server.py is 2500+ lines)

## Technical Architecture

### Tech Stack
- **Frontend**: React, Tailwind CSS, react-router-dom, lucide-react, recharts, framer-motion
- **Backend**: FastAPI, MongoDB (pymongo), JWT auth
- **Integrations**: Twilio (VoIP), Emergent LLM Key (AI features, Whisper STT), Resend (email notifications)

### Key Files
- `/app/backend/server.py` - All API endpoints
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