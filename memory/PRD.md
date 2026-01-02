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
- [x] Call recording toggle
- [x] Email modal from lead records
- [x] Meeting scheduling from lead records
- [x] Activity history timeline per lead
- [x] Bulk email selection

### Collaboration & Productivity
- [x] Team Calendar (fullcalendar.io integration)
- [x] **Calendly-like Booking System** - Public booking pages for each user
  - Date and time slot selection
  - Lead details form
  - Creates calendar event + lead record
  - Accessible via `/book/:userId`
  - **Email notifications** via Resend when bookings are made
- [x] Task management (Outreach-like)
- [x] Team messaging with channels
- [x] Call lists for employees

### AI Features
- [x] AI Copilot/Assistant (floating chatbot widget)
- [x] AI-powered lead insights
- [x] Call Analytics page (Gong-like dashboard)

## Implementation Status

### Completed Features (January 2, 2026)
1. **Booking System (Calendly-like)**
   - Public booking page at `/book/:userId`
   - Available time slot fetching based on calendar
   - Booking creates calendar event + lead if new
   - 30-minute meeting slots, 9 AM - 5 PM
   - **Email notifications** to employees when bookings are made (via Resend)
   - **Guest confirmation emails** with meeting details and preparation tips

2. **Admin User Management**
   - `/admin/users` page for admins
   - Create users with all required fields
   - Edit user details (name, role, department, phone)
   - Delete users (with self-deletion prevention)
   - Copy booking link for each user

### Backend Endpoints
- `/api/booking/{user_id}` - Get user info for booking
- `/api/booking/{user_id}/slots` - Get available slots
- `/api/booking/{user_id}/book` - Create booking
- `/api/admin/users` - CRUD for user management
- `/api/team-members` - List team members

### Frontend Routes
- `/book/:userId` - Public booking page
- `/admin/users` - Admin user management

## Upcoming Tasks (P1)
- [ ] OpenAI Whisper transcription for call recordings
- [ ] Gong-like AI analysis (sentiment, talk-ratio, coaching)

## Future/Backlog (P2)
- [ ] Content Hub (Google Drive integration)
- [ ] CRM Integrations (HubSpot, Salesforce)
- [ ] Screen sharing for meetings

## Technical Architecture

### Tech Stack
- **Frontend**: React, Tailwind CSS, react-router-dom, lucide-react
- **Backend**: FastAPI, MongoDB (pymongo), JWT auth
- **Integrations**: Twilio (VoIP), Emergent LLM Key (AI features), Resend (email notifications)

### Key Files
- `/app/backend/server.py` - All API endpoints
- `/app/frontend/src/pages/BookingPage.js` - Public booking UI
- `/app/frontend/src/pages/AdminUsersPage.js` - Admin user management
- `/app/frontend/src/pages/CalendarPage.js` - Team calendar

## Test Credentials
- Admin: `admin@test.com` / `admin123`
- Test User ID for booking: `9a23a45f-4d64-44fb-980f-f6e06816c8f4`
