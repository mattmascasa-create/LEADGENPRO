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

### Lead Management
- [x] Lead CRUD operations
- [x] Lead scoring (AI-powered)
- [x] Lead status and stage tracking
- [x] Bulk CSV import
- [x] Website scraping for contacts
- [x] Lead distribution by admins
- [x] Drag-and-drop Kanban pipeline

### Sales Workflow & Communication
- [x] Click-to-call via Twilio VoIP
- [x] **Physical Phone Dialer** - Fully functional dial pad with:
  - T9 keypad for entering any phone number
  - Call recording toggle
  - Live call timer
  - Mute/Speaker/Recording controls during call
  - End call button
- [x] **Twilio Integration** - Robust call handling with:
  - Proper webhook endpoints for call status events (`/api/voice/events`)
  - Recording completion callbacks (`/api/voice/recording-callback`)
  - Dial status tracking (`/api/voice/dial-status`)
  - Active call tracking in database
  - Automatic call log creation on completion
  - Recording URL storage for playback
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

## Implementation Status - January 3, 2026

### Completed This Session
1. **Advanced Reporting Dashboard**
   - Created `/reports` route and `AdvancedReportingPage.js`
   - Added to sidebar navigation
   - Comprehensive charts using recharts library
   - Real-time data from API endpoints

2. **Enhanced Team Chat**
   - @mentions with autocomplete (type @ to see team members)
   - File attachment UI (image and document support)
   - Read receipts with checkmarks (delivered/read)
   - Threaded conversations UI
   - Calendly-like availability modal for team members
   - Copy booking link functionality
   - Meeting scheduler integration
   - **Fixed**: Close/minimize button now works properly

3. **AI Sales Coach Enhancement**
   - Added "Next Actions" tab with proactive suggestions
   - Time-based productivity tips
   - Stats-based action items (follow-ups, hot leads)
   - Today's snapshot with key metrics
   - Fixed widget positioning to avoid overlap with AI Copilot

4. **AI Email Generation**
   - Verified "Generate" button fully functional with LLM integration
   - Creates professional sales emails with personalization variables

5. **Bug Fixes**
   - Fixed Team Chat widget not closing when X button clicked
   - Removed duplicate TeamChat component rendering
   - **CRITICAL FIX**: Moved AI Assistant and AI Copilot buttons from left side (behind sidebar) to right side (visible and clickable)
   - All 3 floating widgets (AI Copilot, AI Sales Coach, Team Chat) now properly positioned and accessible

### Backend Endpoints
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
