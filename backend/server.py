from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, UploadFile, File, Form, Request
from fastapi.responses import Response, RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from emergentintegrations.llm.chat import LlmChat, UserMessage
import asyncio
import csv
import io
import re
import aiohttp
from bs4 import BeautifulSoup
from twilio.rest import Client as TwilioClient
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse
import resend
from emergentintegrations.llm.openai import OpenAISpeechToText
import httpx
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
import tempfile
from pywebpush import webpush, WebPushException

# Import modular routes
from routes import (
    notifications_router, push_router, auth_router, leads_router,
    calendar_router, calls_router, chat_router, booking_router, admin_router,
    email_router, forecasting_router, google_router, tasks_router, 
    meetings_router, public_api_router, support_router, stats_router,
    call_analysis_router, workflows_router, deal_velocity_router
)
from routes.notifications import (
    NotificationType, SmartNotification, NotificationPreferences,
    send_push_to_user, should_send_notification, create_lead_assigned_notification
)
# Note: Many models (Lead, Activity, etc.) are defined locally in this file for legacy endpoints
from routes.chat import Channel, ChatMessage, ChatMessageCreate, UserStatus, STATUS_PRESETS, UpdateStatusRequest
from routes.booking import BookingRequest, AvailabilitySlot
from routes.admin import AdminUserCreate, AdminUserUpdate, DailyGoals
from routes.google import CalendarSyncRequest, get_google_credentials, get_drive_service, get_calendar_service, GOOGLE_SCOPES
from routes.tasks import Task, TaskCreate
from routes.meetings import MeetingType, MeetingTypeCreate, AvailabilityRule
from routes.public_api import APIKey, CreateAPIKeyRequest, get_api_key_user
from routes.support import ErrorSeverity, ErrorCategory, categorize_error, log_error_to_db, attempt_auto_fix
from routes.stats import Stats, AIInsight
from routes.call_analysis import CallTranscript, CallAnalysis
from routes.workflows import Workflow, WorkflowAction, WorkflowTrigger
from routes.deal_velocity import record_stage_transition, STAGE_ORDER

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET')
ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_API_KEY = os.environ.get('TWILIO_API_KEY')
TWILIO_API_SECRET = os.environ.get('TWILIO_API_SECRET')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# Initialize Twilio client
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Resend configuration
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Admin emails - these users always have admin privileges
ADMIN_EMAILS = ['mattmascasa@gmail.com', 'monika.iordanoff@gmail.com', 'admin@test.com']

# Emergent LLM Key for AI-powered diagnostics
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# VAPID Keys for Web Push Notifications
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '').replace('\\n', '\n')

# Create the main app and router
app = FastAPI(title="LeadGen Pro API")
api_router = APIRouter(prefix="/api")

# Models
class UserRole(str):
    ADMIN = "admin"
    CLIENT = "client"
    EMPLOYEE = "employee"

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    role: str
    company: Optional[str] = None
    phone: Optional[str] = None  # Agent's phone for click-to-call
    department: Optional[str] = None
    onboarding_completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str
    company: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    mobile: Optional[str] = None
    company: str
    title: Optional[str] = None
    # Company Address fields
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    # Notes
    notes: Optional[str] = None
    status: str = "new"
    stage: str = "prospecting"
    score: int = 0
    deal_value: Optional[float] = 0.0  # Deal value for pipeline forecasting
    ai_insights: Optional[str] = None
    assigned_to: Optional[str] = None
    created_by: str
    last_contacted: Optional[datetime] = None
    tags: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    mobile: Optional[str] = None
    company: str
    title: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    notes: Optional[str] = None
    status: str = "new"
    deal_value: Optional[float] = 0.0
    tags: List[str] = []

class Appointment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    lead_id: Optional[str] = None
    employee_id: str
    scheduled_at: datetime
    duration: int = 30
    status: str = "scheduled"
    meeting_link: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AppointmentCreate(BaseModel):
    title: str
    lead_id: Optional[str] = None
    employee_id: str
    scheduled_at: datetime
    duration: int = 30
    meeting_link: Optional[str] = None
    notes: Optional[str] = None

class EmailSequence(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    active: bool = True
    status: str = "active"  # active, paused, archived
    trigger: str = "manual"  # manual, lead_created, stage_change
    exit_on_reply: bool = True
    exit_on_meeting: bool = True
    total_enrolled: int = 0
    total_completed: int = 0
    total_replied: int = 0
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

class EmailSequenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]] = []

class EmailTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject: str
    body: str
    category: str = "general"
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    body: str
    category: str = "general"

class Activity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    description: str
    lead_id: Optional[str] = None
    user_id: str
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Call/Voice Models
class CallOutcome(str):
    CONNECTED = "connected"
    VOICEMAIL = "voicemail"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    WRONG_NUMBER = "wrong_number"
    DECLINED = "declined"

class CallLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: Optional[str] = None
    phone_number: str
    outcome: str  # connected, no_answer, voicemail, etc.
    disposition: Optional[str] = None  # Left VM, Set Meeting, Not Interested, Bad Number, Wrong POC, Gatekeeper, etc.
    duration: int = 0  # in seconds
    notes: Optional[str] = None
    call_sid: Optional[str] = None
    agent_id: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CallLogCreate(BaseModel):
    lead_id: Optional[str] = None
    phone_number: str
    outcome: str
    disposition: Optional[str] = None
    duration: int = 0
    notes: Optional[str] = None
    call_sid: Optional[str] = None

# Call Disposition Options
CALL_DISPOSITIONS = [
    "No Answer",
    "Left Voicemail", 
    "Gatekeeper",
    "Bad Number",
    "No Longer with Company",
    "Wrong POC",
    "Not Interested",
    "Referral",
    "Call Back",
    "Set Meeting",
    "Sent Info",
    "DNC - Do Not Call"
]

class VoiceTokenRequest(BaseModel):
    identity: str

# Calendar Models
class CalendarEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    type: str = "meeting"  # meeting, call, task, reminder
    start: datetime
    end: datetime
    attendees: List[str] = []
    attendee_names: List[str] = []
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "meeting"
    start: datetime
    end: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    meeting_link: Optional[str] = None

# AI Assistant Models
class AssistantChatRequest(BaseModel):
    message: str
    context: str = "general"

    confidence_factors: List[str] = []
    risk_factors: List[str] = []
    ai_recommendation: Optional[str] = None
    forecast_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Stats(BaseModel):
    total_leads: int
    total_users: int
    total_appointments: int
    conversion_rate: float
    avg_response_time: float
    pipeline_value: float

class AIInsight(BaseModel):
    insight_type: str
    message: str
    confidence: float
    lead_id: Optional[str] = None
    action_items: List[str] = []

# Helper functions
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

async def generate_ai_insight(lead_data: dict) -> str:
    """Generate AI insights for a lead using Emergent LLM"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"lead-analysis-{lead_data.get('id', 'unknown')}",
            system_message="You are an AI sales assistant. Analyze leads and provide actionable insights."
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""Analyze this lead and provide a brief insight (2-3 sentences):
        
        Name: {lead_data.get('first_name')} {lead_data.get('last_name')}
        Company: {lead_data.get('company')}
        Title: {lead_data.get('title', 'Unknown')}
        Email: {lead_data.get('email')}
        Status: {lead_data.get('status')}
        
        Provide: 1) Lead quality assessment, 2) Recommended next action, 3) Potential objections to prepare for."""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        return response
    except Exception as e:
        logging.error(f"AI insight generation failed: {e}")
        return "AI insights currently unavailable. Manual review recommended."

async def calculate_lead_score(lead_data: dict) -> int:
    """Calculate lead score based on various factors"""
    score = 0
    
    # Company domain score
    if lead_data.get('email', '').split('@')[1] if '@' in lead_data.get('email', '') else '':
        score += 20
    
    # Title score
    if lead_data.get('title'):
        senior_titles = ['ceo', 'cto', 'vp', 'director', 'head', 'chief']
        if any(title in lead_data.get('title', '').lower() for title in senior_titles):
            score += 30
        else:
            score += 10
    
    # Contact info completeness
    if lead_data.get('phone'):
        score += 15
    if lead_data.get('email'):
        score += 15
    
    # Tags
    score += min(len(lead_data.get('tags', [])) * 5, 20)
    
    return min(score, 100)

async def send_booking_notification_email(
    employee_email: str,
    employee_name: str,
    guest_name: str,
    guest_email: str,
    guest_phone: str,
    guest_company: str,
    booking_datetime: datetime,
    duration: int,
    notes: str
):
    """Send email notification to employee when someone books a meeting"""
    if not RESEND_API_KEY:
        logging.warning("RESEND_API_KEY not configured, skipping email notification")
        return None
    
    # Format the datetime nicely
    formatted_date = booking_datetime.strftime("%A, %B %d, %Y")
    formatted_time = booking_datetime.strftime("%I:%M %p")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%); padding: 30px; border-radius: 12px 12px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">New Meeting Booked!</h1>
        </div>
        
        <div style="background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
            <p style="font-size: 16px; margin-bottom: 20px;">Hi {employee_name},</p>
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                <strong>{guest_name}</strong> has booked a meeting with you via your LeadGen Pro booking page.
            </p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
                <h2 style="color: #3b82f6; margin-top: 0; font-size: 18px;">Meeting Details</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; width: 120px;">Date:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{formatted_date}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Time:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{formatted_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Duration:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{duration} minutes</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
                <h2 style="color: #3b82f6; margin-top: 0; font-size: 18px;">Guest Information</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; width: 120px;">Name:</td>
                        <td style="padding: 8px 0;">{guest_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Email:</td>
                        <td style="padding: 8px 0;"><a href="mailto:{guest_email}" style="color: #3b82f6;">{guest_email}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Phone:</td>
                        <td style="padding: 8px 0;">{guest_phone or 'Not provided'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Company:</td>
                        <td style="padding: 8px 0;">{guest_company or 'Not provided'}</td>
                    </tr>
                </table>
            </div>
            
            {f'''<div style="background: #fef3c7; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b; margin-bottom: 20px;">
                <strong style="color: #92400e;">Notes from guest:</strong>
                <p style="margin: 10px 0 0 0; color: #78350f;">{notes}</p>
            </div>''' if notes else ''}
            
            <p style="font-size: 14px; color: #64748b; margin-top: 20px;">
                This meeting has been automatically added to your LeadGen Pro calendar.
            </p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; text-align: center;">
                <p style="font-size: 12px; color: #94a3b8; margin: 0;">
                    Powered by LeadGen Pro
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    params = {
        "from": SENDER_EMAIL,
        "to": [employee_email],
        "subject": f"New Meeting Booked: {guest_name} on {formatted_date}",
        "html": html_content
    }
    
    try:
        email = await asyncio.to_thread(resend.Emails.send, params)
        logging.info(f"Booking notification email sent to {employee_email}, email_id: {email.get('id')}")
        return email
    except Exception as e:
        logging.error(f"Failed to send booking notification email: {str(e)}")
        return None

async def send_guest_confirmation_email(
    guest_name: str,
    guest_email: str,
    employee_name: str,
    employee_email: str,
    booking_datetime: datetime,
    duration: int,
    company_name: str = "LeadGen Pro"
):
    """Send confirmation email to guest after they book a meeting"""
    if not RESEND_API_KEY:
        logging.warning("RESEND_API_KEY not configured, skipping guest confirmation email")
        return None
    
    # Format the datetime nicely
    formatted_date = booking_datetime.strftime("%A, %B %d, %Y")
    formatted_time = booking_datetime.strftime("%I:%M %p")
    
    # Calculate end time
    end_time = (booking_datetime + timedelta(minutes=duration)).strftime("%I:%M %p")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; border-radius: 12px 12px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Meeting Confirmed!</h1>
        </div>
        
        <div style="background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
            <p style="font-size: 16px; margin-bottom: 20px;">Hi {guest_name},</p>
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                Your meeting with <strong>{employee_name}</strong> has been confirmed. We're looking forward to speaking with you!
            </p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
                <h2 style="color: #10b981; margin-top: 0; font-size: 18px;">Meeting Details</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; width: 120px;">Date:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{formatted_date}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Time:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{formatted_time} - {end_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Duration:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{duration} minutes</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">With:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{employee_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Type:</td>
                        <td style="padding: 8px 0; font-weight: bold;">Video or Phone Call</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #ecfdf5; padding: 20px; border-radius: 8px; border-left: 4px solid #10b981; margin-bottom: 20px;">
                <h3 style="color: #065f46; margin-top: 0; font-size: 16px;">Before Your Meeting</h3>
                <ul style="margin: 10px 0 0 0; padding-left: 20px; color: #047857;">
                    <li style="margin-bottom: 8px;">Add this meeting to your calendar</li>
                    <li style="margin-bottom: 8px;">Prepare any questions or topics you'd like to discuss</li>
                    <li style="margin-bottom: 8px;">Ensure you have a stable internet connection for video calls</li>
                    <li style="margin-bottom: 0;">Find a quiet place for the call</li>
                </ul>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
                <h3 style="color: #374151; margin-top: 0; font-size: 16px;">Need to reschedule?</h3>
                <p style="margin: 0; color: #64748b; font-size: 14px;">
                    If you need to change the time of your meeting, please contact us at 
                    <a href="mailto:{employee_email}" style="color: #3b82f6;">{employee_email}</a>
                </p>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; text-align: center;">
                <p style="font-size: 12px; color: #94a3b8; margin: 0;">
                    Powered by LeadGen Pro
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    params = {
        "from": SENDER_EMAIL,
        "to": [guest_email],
        "subject": f"Meeting Confirmed: {formatted_date} at {formatted_time} with {employee_name}",
        "html": html_content
    }
    
    try:
        email = await asyncio.to_thread(resend.Emails.send, params)
        logging.info(f"Guest confirmation email sent to {guest_email}, email_id: {email.get('id')}")
        return email
    except Exception as e:
        logging.error(f"Failed to send guest confirmation email: {str(e)}")
        return None


# Email Sequences
@api_router.get("/sequences", response_model=List[EmailSequence])
async def get_sequences(current_user: User = Depends(get_current_user)):
    sequences = await db.sequences.find({}, {"_id": 0}).to_list(1000)
    return [EmailSequence(**seq) for seq in sequences]

@api_router.post("/sequences", response_model=EmailSequence)
async def create_sequence(seq_data: EmailSequenceCreate, current_user: User = Depends(get_current_user)):
    sequence = EmailSequence(**seq_data.model_dump(), created_by=current_user.id)
    doc = sequence.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.sequences.insert_one(doc)
    return sequence

# Email Templates
@api_router.get("/templates", response_model=List[EmailTemplate])
async def get_templates(current_user: User = Depends(get_current_user)):
    templates = await db.templates.find({}, {"_id": 0}).to_list(1000)
    return [EmailTemplate(**tmpl) for tmpl in templates]

@api_router.post("/templates", response_model=EmailTemplate)
async def create_template(tmpl_data: EmailTemplateCreate, current_user: User = Depends(get_current_user)):
    template = EmailTemplate(**tmpl_data.model_dump(), created_by=current_user.id)
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.templates.insert_one(doc)
    return template

# Activities
@api_router.get("/activities", response_model=List[Activity])
async def get_activities(limit: int = 50, lead_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    activities = await db.activities.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return [Activity(**act) for act in activities]

class ActivityCreate(BaseModel):
    type: str
    description: str
    lead_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

@api_router.post("/activities", response_model=Activity)
async def create_activity(activity_data: ActivityCreate, current_user: User = Depends(get_current_user)):
    """Create a new activity"""
    activity = Activity(
        **activity_data.model_dump(),
        user_id=current_user.id
    )
    doc = activity.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.activities.insert_one(doc)
    return activity

# Stats routes
class CallListItem(BaseModel):
    lead: Lead
    call_status: Optional[str] = None
    last_call_attempt: Optional[datetime] = None
    notes: Optional[str] = None

@api_router.get("/call-list")
async def get_call_list(current_user: User = Depends(get_current_user)):
    """Get daily call list for employee"""
    if current_user.role not in ["employee", "admin"]:
        raise HTTPException(status_code=403, detail="Employee access required")
    
    # Get assigned leads that need calling
    leads = await db.leads.find({
        "assigned_to": current_user.id,
        "status": {"$in": ["new", "contacted", "follow_up"]}
    }, {"_id": 0}).to_list(1000)
    
    # Get call history
    call_history = await db.call_logs.find({
        "employee_id": current_user.id
    }, {"_id": 0}).to_list(1000)
    
    call_history_dict = {log['lead_id']: log for log in call_history}
    
    call_list = []
    for lead_doc in leads:
        lead = Lead(**lead_doc)
        history = call_history_dict.get(lead.id, {})
        call_list.append({
            "lead": lead,
            "call_status": history.get('status'),
            "last_call_attempt": history.get('last_attempt'),
            "notes": history.get('notes')
        })
    
    return {
        "total_calls": len(call_list),
        "call_list": call_list
    }

# Log Call Outcome
class CallOutcomeRequest(BaseModel):
    lead_id: str
    outcome: str  # contacted, no_answer, voicemail, wrong_number, meeting_scheduled
    notes: Optional[str] = None
    meeting_scheduled_at: Optional[datetime] = None

@api_router.post("/call-log")
async def log_call_outcome(
    outcome: CallOutcomeRequest,
    current_user: User = Depends(get_current_user)
):
    """Log the outcome of a call"""
    # Update lead status
    update_data = {
        "status": "contacted" if outcome.outcome == "contacted" else "follow_up",
        "last_contacted": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # If meeting scheduled, update lead stage
    if outcome.outcome == "meeting_scheduled":
        update_data["stage"] = "qualified"
        update_data["status"] = "meeting_scheduled"
    
    await db.leads.update_one(
        {"id": outcome.lead_id},
        {"$set": update_data}
    )
    
    # Log the call
    call_log = {
        "id": str(uuid.uuid4()),
        "lead_id": outcome.lead_id,
        "employee_id": current_user.id,
        "outcome": outcome.outcome,
        "notes": outcome.notes,
        "meeting_scheduled_at": outcome.meeting_scheduled_at.isoformat() if outcome.meeting_scheduled_at else None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.call_logs.insert_one(call_log)
    
    # Log activity
    activity = Activity(
        type="call_logged",
        description=f"Call outcome: {outcome.outcome}",
        lead_id=outcome.lead_id,
        user_id=current_user.id,
        metadata={"outcome": outcome.outcome}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return {"message": "Call logged successfully", "outcome": outcome.outcome}


# =============================================================================
# SMART ERROR HANDLING & SUPPORT BOT ENDPOINTS
# =============================================================================

class ErrorReport(BaseModel):
    error_type: str
    error_message: str
    endpoint: Optional[str] = None
    stack_trace: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    user_agent: Optional[str] = None
    page_url: Optional[str] = None

class SupportBotRequest(BaseModel):
    error_id: Optional[str] = None
    question: str
    context: Optional[Dict[str, Any]] = None

@api_router.get("/notifications")
async def get_notifications(current_user: User = Depends(get_current_user)):
    """Get user notifications including error alerts"""
    notifications = []
    
    is_admin = current_user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or current_user.role == 'admin'
    
    if is_admin:
        # Get unresolved critical errors
        critical_errors = await db.system_errors.find(
            {"severity": "critical", "resolved": False},
            {"_id": 0}
        ).sort("created_at", -1).limit(5).to_list(5)
        
        for error in critical_errors:
            notifications.append({
                "id": error["id"],
                "type": "error",
                "severity": "critical",
                "title": f"Critical Error: {error['error_type']}",
                "message": error["error_message"][:100] + "..." if len(error.get("error_message", "")) > 100 else error.get("error_message", ""),
                "created_at": error["created_at"],
                "action_url": f"/admin/errors/{error['id']}"
            })
        
        # Get recent high severity errors
        high_errors = await db.system_errors.find(
            {"severity": "high", "resolved": False},
            {"_id": 0}
        ).sort("created_at", -1).limit(3).to_list(3)
        
        for error in high_errors:
            notifications.append({
                "id": error["id"],
                "type": "error",
                "severity": "high",
                "title": f"Error: {error['error_type']}",
                "message": error["error_message"][:100] + "..." if len(error.get("error_message", "")) > 100 else error.get("error_message", ""),
                "created_at": error["created_at"],
                "action_url": f"/admin/errors/{error['id']}"
            })
    
    # Get user-specific notifications
    user_notifications = await db.notifications.find(
        {"user_id": current_user.id, "read": False},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    notifications.extend(user_notifications)
    
    # Sort by created_at
    notifications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "notifications": notifications[:15],
        "unread_count": len([n for n in notifications if not n.get("read", False)])
    }

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read"""
    await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Notification marked as read"}


# Include modular routers
app.include_router(notifications_router, prefix="/api")
app.include_router(push_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(leads_router, prefix="/api")
app.include_router(calendar_router, prefix="/api")
app.include_router(calls_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(booking_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(email_router, prefix="/api")
app.include_router(forecasting_router, prefix="/api")
app.include_router(google_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(meetings_router, prefix="/api")
app.include_router(public_api_router, prefix="/api")
app.include_router(support_router, prefix="/api")
app.include_router(stats_router, prefix="/api")

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()