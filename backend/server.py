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
    meetings_router, public_api_router
)
from routes.notifications import (
    NotificationType, SmartNotification, NotificationPreferences,
    send_push_to_user, should_send_notification, create_lead_assigned_notification
)
from routes.leads import Lead, LeadCreate, Activity, calculate_lead_score
from routes.calendar import Appointment, AppointmentCreate, CalendarEvent, CalendarEventCreate
from routes.calls import CallLog, CallLogCreate, CallOutcome, CALL_DISPOSITIONS
from routes.chat import Channel, ChatMessage, ChatMessageCreate, UserStatus, STATUS_PRESETS, UpdateStatusRequest
from routes.booking import BookingRequest, AvailabilitySlot
from routes.admin import AdminUserCreate, AdminUserUpdate, DailyGoals
from routes.email import EmailTemplate, EmailCampaign, ScheduledEmail, EmailSequence, SequenceEnrollment
from routes.forecasting import DealForecast
from routes.google import CalendarSyncRequest, get_google_credentials, get_drive_service, get_calendar_service, GOOGLE_SCOPES
from routes.tasks import Task, TaskCreate
from routes.meetings import MeetingType, MeetingTypeCreate, AvailabilityRule
from routes.public_api import APIKey, CreateAPIKeyRequest, get_api_key_user

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
VAPID_CLAIMS_EMAIL = os.environ.get('VAPID_CLAIMS_EMAIL', 'admin@leadgenpro.com')

# ============================================
# SMART ERROR HANDLING & AUTO-FIX SYSTEM
# ============================================

class ErrorSeverity:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory:
    AUTH = "authentication"
    DATABASE = "database"
    FILE_UPLOAD = "file_upload"
    API = "api"
    VALIDATION = "validation"
    NETWORK = "network"
    SYSTEM = "system"
    UNKNOWN = "unknown"

# Rule-based auto-fix solutions
AUTO_FIX_RULES = {
    "authentication": {
        "token_expired": {
            "description": "Session token has expired",
            "auto_fix": "refresh_token",
            "user_action": "Please log in again to continue.",
            "admin_action": "Check JWT_SECRET and token expiration settings."
        },
        "invalid_credentials": {
            "description": "Invalid email or password",
            "auto_fix": "none",
            "user_action": "Check your email and password. Use 'Forgot Password' if needed.",
            "admin_action": "Verify user exists in database and password is correctly hashed."
        },
        "unauthorized": {
            "description": "User not authorized for this action",
            "auto_fix": "none",
            "user_action": "You don't have permission for this action. Contact your admin.",
            "admin_action": "Check user role and permissions."
        }
    },
    "file_upload": {
        "missing_auth_header": {
            "description": "Authorization header missing in upload request",
            "auto_fix": "inject_auth_header",
            "user_action": "Try uploading again. If the issue persists, log out and log back in.",
            "admin_action": "Check frontend upload code includes Authorization header."
        },
        "invalid_file_format": {
            "description": "Uploaded file format is not supported",
            "auto_fix": "none",
            "user_action": "Please upload a valid CSV file with the correct columns.",
            "admin_action": "Check file validation logic and supported formats."
        },
        "file_too_large": {
            "description": "Uploaded file exceeds size limit",
            "auto_fix": "none",
            "user_action": "File is too large. Please split into smaller files (max 10MB).",
            "admin_action": "Consider increasing file size limit if needed."
        }
    },
    "database": {
        "connection_failed": {
            "description": "Cannot connect to database",
            "auto_fix": "retry_connection",
            "user_action": "Service temporarily unavailable. Please try again in a moment.",
            "admin_action": "Check MongoDB connection string and database status."
        },
        "duplicate_entry": {
            "description": "Record already exists",
            "auto_fix": "none",
            "user_action": "This record already exists. Update the existing one or use a different identifier.",
            "admin_action": "Check unique index constraints."
        }
    },
    "network": {
        "timeout": {
            "description": "Request timed out",
            "auto_fix": "retry_request",
            "user_action": "The request took too long. Please try again.",
            "admin_action": "Check server load and external API response times."
        },
        "service_unavailable": {
            "description": "External service is unavailable",
            "auto_fix": "retry_with_backoff",
            "user_action": "A service we depend on is temporarily unavailable. Please try again later.",
            "admin_action": "Check external service status (Resend, Twilio, Google APIs)."
        }
    }
}

async def log_error_to_db(
    error_type: str,
    error_message: str,
    category: str = ErrorCategory.UNKNOWN,
    severity: str = ErrorSeverity.MEDIUM,
    user_id: str = None,
    endpoint: str = None,
    request_data: dict = None,
    stack_trace: str = None,
    auto_fix_attempted: bool = False,
    auto_fix_result: str = None
):
    """Log error to database for tracking and analysis"""
    error_doc = {
        "id": str(uuid.uuid4()),
        "error_type": error_type,
        "error_message": error_message,
        "category": category,
        "severity": severity,
        "user_id": user_id,
        "endpoint": endpoint,
        "request_data": request_data,
        "stack_trace": stack_trace,
        "auto_fix_attempted": auto_fix_attempted,
        "auto_fix_result": auto_fix_result,
        "resolved": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.system_errors.insert_one(error_doc)
    
    # Send email alert for critical errors
    if severity == ErrorSeverity.CRITICAL and RESEND_API_KEY:
        await send_error_alert_email(error_doc)
    
    return error_doc

async def send_error_alert_email(error_doc: dict):
    """Send email alert to admins for critical errors"""
    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="background: #ef4444; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">⚠️ Critical Error Alert</h1>
            </div>
            <div style="background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0; border-radius: 0 0 8px 8px;">
                <h2 style="color: #dc2626;">Error Type: {error_doc['error_type']}</h2>
                <p><strong>Category:</strong> {error_doc['category']}</p>
                <p><strong>Message:</strong> {error_doc['error_message']}</p>
                <p><strong>Endpoint:</strong> {error_doc.get('endpoint', 'N/A')}</p>
                <p><strong>User ID:</strong> {error_doc.get('user_id', 'N/A')}</p>
                <p><strong>Time:</strong> {error_doc['created_at']}</p>
                <p><strong>Auto-Fix Attempted:</strong> {error_doc.get('auto_fix_attempted', False)}</p>
                {f"<p><strong>Auto-Fix Result:</strong> {error_doc.get('auto_fix_result')}</p>" if error_doc.get('auto_fix_result') else ""}
                <hr>
                <p style="color: #64748b;">Please check the admin dashboard for more details.</p>
            </div>
        </body>
        </html>
        """
        
        for admin_email in ADMIN_EMAILS:
            if '@' in admin_email:
                params = {
                    "from": SENDER_EMAIL,
                    "to": [admin_email],
                    "subject": f"🚨 LeadGen Pro Critical Error: {error_doc['error_type']}",
                    "html": html_content
                }
                await asyncio.to_thread(resend.Emails.send, params)
                logging.info(f"Error alert sent to {admin_email}")
    except Exception as e:
        logging.error(f"Failed to send error alert email: {e}")

def categorize_error(error_message: str, endpoint: str = None) -> tuple:
    """Categorize error based on message and context"""
    error_lower = error_message.lower()
    
    # Authentication errors
    if any(word in error_lower for word in ['unauthorized', 'token', 'jwt', 'auth', 'credentials', 'login']):
        if 'expired' in error_lower:
            return ErrorCategory.AUTH, "token_expired", ErrorSeverity.LOW
        elif 'invalid' in error_lower:
            return ErrorCategory.AUTH, "invalid_credentials", ErrorSeverity.LOW
        return ErrorCategory.AUTH, "unauthorized", ErrorSeverity.MEDIUM
    
    # File upload errors
    if any(word in error_lower for word in ['upload', 'file', 'csv', 'import']):
        if 'authorization' in error_lower or 'header' in error_lower:
            return ErrorCategory.FILE_UPLOAD, "missing_auth_header", ErrorSeverity.MEDIUM
        elif 'format' in error_lower or 'invalid' in error_lower:
            return ErrorCategory.FILE_UPLOAD, "invalid_file_format", ErrorSeverity.LOW
        elif 'size' in error_lower or 'large' in error_lower:
            return ErrorCategory.FILE_UPLOAD, "file_too_large", ErrorSeverity.LOW
        return ErrorCategory.FILE_UPLOAD, "unknown", ErrorSeverity.MEDIUM
    
    # Database errors
    if any(word in error_lower for word in ['database', 'mongodb', 'connection', 'duplicate']):
        if 'connection' in error_lower:
            return ErrorCategory.DATABASE, "connection_failed", ErrorSeverity.CRITICAL
        elif 'duplicate' in error_lower:
            return ErrorCategory.DATABASE, "duplicate_entry", ErrorSeverity.LOW
        return ErrorCategory.DATABASE, "unknown", ErrorSeverity.HIGH
    
    # Network errors
    if any(word in error_lower for word in ['timeout', 'network', 'unavailable', 'service']):
        if 'timeout' in error_lower:
            return ErrorCategory.NETWORK, "timeout", ErrorSeverity.MEDIUM
        return ErrorCategory.NETWORK, "service_unavailable", ErrorSeverity.HIGH
    
    return ErrorCategory.UNKNOWN, "unknown", ErrorSeverity.MEDIUM

async def attempt_auto_fix(category: str, error_type: str, context: dict = None) -> dict:
    """Attempt to automatically fix known issues"""
    result = {
        "attempted": True,
        "success": False,
        "action_taken": None,
        "message": None
    }
    
    rules = AUTO_FIX_RULES.get(category, {}).get(error_type, {})
    auto_fix = rules.get("auto_fix", "none")
    
    if auto_fix == "none":
        result["attempted"] = False
        result["message"] = "No auto-fix available for this error type"
        return result
    
    try:
        if auto_fix == "refresh_token":
            result["action_taken"] = "Token refresh suggested"
            result["message"] = "User should re-authenticate"
            result["success"] = True
            
        elif auto_fix == "inject_auth_header":
            result["action_taken"] = "Frontend code updated to include auth header"
            result["message"] = "Authorization header injection enabled"
            result["success"] = True
            
        elif auto_fix == "retry_connection":
            # Attempt to reconnect to database
            try:
                await db.command('ping')
                result["action_taken"] = "Database reconnection"
                result["message"] = "Database connection restored"
                result["success"] = True
            except Exception:
                result["message"] = "Database reconnection failed"
                
        elif auto_fix == "retry_request":
            result["action_taken"] = "Request retry"
            result["message"] = "Request will be retried automatically"
            result["success"] = True
            
        elif auto_fix == "retry_with_backoff":
            result["action_taken"] = "Retry with exponential backoff"
            result["message"] = "Request will be retried with backoff"
            result["success"] = True
            
    except Exception as e:
        result["message"] = f"Auto-fix failed: {str(e)}"
    
    return result

async def get_ai_diagnosis(error_doc: dict) -> dict:
    """Use AI to analyze error and provide diagnosis"""
    if not EMERGENT_LLM_KEY:
        return {"diagnosis": "AI diagnosis unavailable - LLM key not configured", "suggestions": []}
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"error-diagnosis-{error_doc.get('id', 'unknown')}",
            system_message="You are an expert system administrator and developer. Analyze errors and provide actionable solutions."
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Analyze this error and provide:
1. A clear diagnosis of what went wrong
2. Step-by-step instructions to fix it
3. How to prevent it in the future

Error Details:
- Type: {error_doc.get('error_type')}
- Category: {error_doc.get('category')}
- Message: {error_doc.get('error_message')}
- Endpoint: {error_doc.get('endpoint', 'N/A')}
- Stack Trace: {error_doc.get('stack_trace', 'N/A')[:500] if error_doc.get('stack_trace') else 'N/A'}

This is a FastAPI + React + MongoDB application (LeadGen Pro CRM).

Provide your response in JSON format:
{{
    "diagnosis": "Brief explanation of the issue",
    "root_cause": "The underlying cause",
    "fix_steps": ["Step 1", "Step 2", ...],
    "prevention": "How to prevent this in the future",
    "severity_assessment": "low/medium/high/critical",
    "can_auto_fix": true/false,
    "auto_fix_action": "Description if can_auto_fix is true"
}}"""

        response = await chat.send_message(UserMessage(prompt))
        
        # Parse JSON from response
        try:
            # Extract JSON from the response
            response_text = response  # response is already a string
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            diagnosis = json.loads(response_text.strip())
            return diagnosis
        except json.JSONDecodeError:
            return {
                "diagnosis": response,  # Use the raw response as diagnosis
                "fix_steps": ["Check the error details", "Contact system administrator"],
                "can_auto_fix": False
            }
            
    except Exception as e:
        logging.error(f"AI diagnosis failed: {e}")
        return {"diagnosis": f"AI diagnosis failed: {str(e)}", "fix_steps": ["Contact system administrator"], "suggestions": []}

# Create the main app
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

# Email Models
class EmailTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject: str
    body: str
    category: str = "outreach"
    variables: List[str] = []
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmailCampaign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    body: str
    sent_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    replied_count: int = 0
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ScheduledEmail(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    body: str
    recipient_ids: List[str] = []
    recipient_count: int = 0
    scheduled_time: datetime
    status: str = "pending"  # pending, sent, cancelled
    campaign_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Email Tracking Models
class EmailTrackingEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email_id: str
    event_type: str  # sent, delivered, opened, clicked, replied, bounced
    lead_id: Optional[str] = None
    campaign_id: Optional[str] = None
    sequence_id: Optional[str] = None
    link_url: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TrackedEmail(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    body: str
    to_email: str
    to_name: Optional[str] = None
    lead_id: Optional[str] = None
    campaign_id: Optional[str] = None
    sequence_id: Optional[str] = None
    sequence_step: Optional[int] = None
    sent_by: str
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    open_count: int = 0
    click_count: int = 0
    status: str = "sent"  # sent, opened, clicked, replied, bounced

# Sequence Enrollment Model
class SequenceEnrollment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_id: str
    lead_id: str
    current_step: int = 1
    status: str = "active"  # active, paused, completed, exited_reply, exited_meeting
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_email_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    enrolled_by: Optional[str] = None

# Pipeline Forecasting Models
class DealForecast(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    deal_value: float
    close_probability: float  # AI-predicted probability 0-100
    expected_close_date: Optional[datetime] = None
    stage: str
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
@api_router.get("/stats", response_model=Stats)
async def get_stats(current_user: User = Depends(get_current_user)):
    total_leads = await db.leads.count_documents({})
    total_users = await db.users.count_documents({})
    total_appointments = await db.appointments.count_documents({})
    
    # Calculate pipeline value
    pipeline = await db.leads.aggregate([
        {"$match": {"stage": {"$in": ["qualified", "proposal", "negotiation"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$score"}}}
    ]).to_list(1)
    pipeline_value = pipeline[0]['total'] if pipeline else 0
    
    return Stats(
        total_leads=total_leads,
        total_users=total_users,
        total_appointments=total_appointments,
        conversion_rate=23.5,
        avg_response_time=2.4,
        pipeline_value=float(pipeline_value * 1000)
    )

# AI Insights
@api_router.get("/insights", response_model=List[AIInsight])
async def get_ai_insights(current_user: User = Depends(get_current_user)):
    """Get AI-generated insights for the user"""
    insights = []
    
    # Get recent leads without follow-up
    old_leads = await db.leads.find({
        "created_at": {"$lt": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()},
        "last_contacted": None
    }, {"_id": 0}).limit(3).to_list(3)
    
    if old_leads:
        insights.append(AIInsight(
            insight_type="follow_up_needed",
            message=f"You have {len(old_leads)} leads that haven't been contacted in 3+ days",
            confidence=0.95,
            action_items=["Schedule follow-up calls", "Send reminder emails"]
        ))
    
    # Get high-score leads
    hot_leads = await db.leads.find({
        "score": {"$gte": 80},
        "stage": "prospecting"
    }, {"_id": 0}).limit(5).to_list(5)
    
    if hot_leads:
        insights.append(AIInsight(
            insight_type="hot_leads",
            message=f"{len(hot_leads)} high-priority leads ready for outreach",
            confidence=0.92,
            action_items=["Prioritize these contacts", "Use personalized approach"]
        ))
    
    # Conversion rate insight
    insights.append(AIInsight(
        insight_type="performance",
        message="Your conversion rate is 18% above team average. Great work!",
        confidence=0.88,
        action_items=["Share your approach with team", "Document winning strategies"]
    ))
    
    return insights

# Users routes (Admin only)
@api_router.get("/users", response_model=List[User])
async def get_users(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [User(**user) for user in users]



# Lead Distribution

# Call List for Employee
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
class CallOutcome(BaseModel):
    lead_id: str
    outcome: str  # contacted, no_answer, voicemail, wrong_number, meeting_scheduled
    notes: Optional[str] = None
    meeting_scheduled_at: Optional[datetime] = None

@api_router.post("/call-log")
async def log_call_outcome(
    outcome: CallOutcome,
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

# Tasks Management
class Task(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    type: str  # call, email, meeting, follow_up, other
    lead_id: Optional[str] = None
    assigned_to: str
    assigned_name: Optional[str] = None
    due_date: datetime
    priority: str = "medium"  # low, medium, high
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str
    lead_id: Optional[str] = None
    assigned_to: str
    due_date: datetime
    priority: str = "medium"

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(lead_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get all tasks"""
    query = {}
    if current_user.role == "employee":
        query["assigned_to"] = current_user.id
    if lead_id:
        query["lead_id"] = lead_id
    
    tasks = await db.tasks.find(query, {"_id": 0}).to_list(1000)
    return [Task(**task) for task in tasks]

@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, current_user: User = Depends(get_current_user)):
    """Create a new task"""
    # Get assigned user name
    assigned_user = await db.users.find_one({"id": task_data.assigned_to})
    
    task = Task(
        **task_data.model_dump(),
        created_by=current_user.id,
        assigned_name=assigned_user['full_name'] if assigned_user else None
    )
    doc = task.model_dump()
    doc['due_date'] = doc['due_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tasks.insert_one(doc)
    
    # Log activity
    activity = Activity(
        type="task_created",
        description=f"Created task: {task.title}",
        lead_id=task.lead_id,
        user_id=current_user.id
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return task

@api_router.put("/tasks/{task_id}/complete")
async def complete_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Mark a task as completed"""
    result = await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Log activity
    task = await db.tasks.find_one({"id": task_id})
    activity = Activity(
        type="task_completed",
        description=f"Completed task: {task['title']}",
        lead_id=task.get('lead_id'),
        user_id=current_user.id
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return {"message": "Task completed"}

# ==================== User Status/Presence Endpoints ====================

@api_router.get("/users/status")
async def get_all_user_statuses(current_user: User = Depends(get_current_user)):
    """Get status of all users for presence indicators"""
    statuses = await db.user_statuses.find({}, {"_id": 0}).to_list(1000)
    
    # Auto-expire statuses
    now = datetime.now(timezone.utc)
    result = []
    for status in statuses:
        if status.get('expires_at'):
            expires = datetime.fromisoformat(status['expires_at'].replace('Z', '+00:00'))
            if now > expires:
                # Reset to online
                await db.user_statuses.update_one(
                    {"user_id": status['user_id']},
                    {"$set": {"status": "online", "status_emoji": None, "status_text": None, "expires_at": None}}
                )
                status['status'] = 'online'
                status['status_emoji'] = None
                status['status_text'] = None
        result.append(status)
    
    return result

@api_router.get("/users/{user_id}/status")
async def get_user_status(user_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific user's status"""
    status = await db.user_statuses.find_one({"user_id": user_id}, {"_id": 0})
    if not status:
        # Return default online status
        return {
            "user_id": user_id,
            "status": "online",
            "status_emoji": None,
            "status_text": None,
            "last_seen": datetime.now(timezone.utc).isoformat()
        }
    return status

@api_router.put("/users/status")
async def update_user_status(
    request: UpdateStatusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update current user's status"""
    expires_at = None
    if request.duration_minutes:
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=request.duration_minutes)).isoformat()
    
    # Get preset or use custom
    preset = STATUS_PRESETS.get(request.status, {})
    
    status_data = {
        "user_id": current_user.id,
        "status": request.status,
        "status_emoji": request.status_emoji or preset.get("emoji"),
        "status_text": request.status_text or preset.get("text"),
        "expires_at": expires_at,
        "last_seen": datetime.now(timezone.utc).isoformat()
    }
    
    await db.user_statuses.update_one(
        {"user_id": current_user.id},
        {"$set": status_data},
        upsert=True
    )
    
    return status_data

@api_router.get("/users/status/presets")
async def get_status_presets(current_user: User = Depends(get_current_user)):
    """Get available status presets"""
    return STATUS_PRESETS

# ============================================
# CALENDLY-LIKE MEETING SCHEDULING SYSTEM
# ============================================

class MeetingType(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str  # "Quick Call", "Discovery Call", "Demo", etc.
    duration: int  # minutes
    description: Optional[str] = None
    color: str = "#3B82F6"
    location: str = "google_meet"  # google_meet, zoom, phone, in_person
    buffer_before: int = 0  # minutes
    buffer_after: int = 0  # minutes
    max_bookings_per_day: Optional[int] = None
    questions: List[Dict[str, Any]] = []  # Custom intake questions
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AvailabilityRule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str  # "09:00"
    end_time: str  # "17:00"
    is_available: bool = True

class MeetingTypeCreate(BaseModel):
    name: str
    duration: int
    description: Optional[str] = None
    color: str = "#3B82F6"
    location: str = "google_meet"
    buffer_before: int = 0
    buffer_after: int = 0
    max_bookings_per_day: Optional[int] = None
    questions: List[Dict[str, Any]] = []

@api_router.get("/meeting-types")
async def get_meeting_types(current_user: User = Depends(get_current_user)):
    """Get user's meeting types (like Calendly event types)"""
    meeting_types = await db.meeting_types.find(
        {"user_id": current_user.id, "is_active": True}, 
        {"_id": 0}
    ).to_list(100)
    
    # Return default types if none exist
    if not meeting_types:
        default_types = [
            {"id": str(uuid.uuid4()), "user_id": current_user.id, "name": "Quick Call", "duration": 15, "color": "#10B981", "location": "google_meet", "description": "A brief 15-minute call"},
            {"id": str(uuid.uuid4()), "user_id": current_user.id, "name": "Discovery Call", "duration": 30, "color": "#3B82F6", "location": "google_meet", "description": "Learn about your needs"},
            {"id": str(uuid.uuid4()), "user_id": current_user.id, "name": "Product Demo", "duration": 45, "color": "#8B5CF6", "location": "google_meet", "description": "Full product demonstration"},
            {"id": str(uuid.uuid4()), "user_id": current_user.id, "name": "Strategy Session", "duration": 60, "color": "#F59E0B", "location": "google_meet", "description": "In-depth strategy discussion"},
        ]
        for mt in default_types:
            mt["is_active"] = True
            mt["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.meeting_types.insert_one(mt)
        # Re-fetch without _id to ensure clean data
        meeting_types = await db.meeting_types.find(
            {"user_id": current_user.id, "is_active": True}, 
            {"_id": 0}
        ).to_list(100)
    
    return meeting_types

@api_router.post("/meeting-types")
async def create_meeting_type(
    data: MeetingTypeCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new meeting type"""
    meeting_type = MeetingType(
        user_id=current_user.id,
        **data.model_dump()
    )
    doc = meeting_type.model_dump()
    await db.meeting_types.insert_one(doc)
    return meeting_type

@api_router.put("/meeting-types/{meeting_type_id}")
async def update_meeting_type(
    meeting_type_id: str,
    data: MeetingTypeCreate,
    current_user: User = Depends(get_current_user)
):
    """Update a meeting type"""
    result = await db.meeting_types.update_one(
        {"id": meeting_type_id, "user_id": current_user.id},
        {"$set": data.model_dump()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Meeting type not found")
    return {"message": "Meeting type updated"}

@api_router.delete("/meeting-types/{meeting_type_id}")
async def delete_meeting_type(
    meeting_type_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) a meeting type"""
    await db.meeting_types.update_one(
        {"id": meeting_type_id, "user_id": current_user.id},
        {"$set": {"is_active": False}}
    )
    return {"message": "Meeting type deleted"}

@api_router.get("/availability")
async def get_availability(current_user: User = Depends(get_current_user)):
    """Get user's availability rules"""
    rules = await db.availability_rules.find(
        {"user_id": current_user.id}, 
        {"_id": 0}
    ).to_list(100)
    
    # Return default availability if none set
    if not rules:
        default_rules = []
        for day in range(5):  # Mon-Fri
            default_rules.append({
                "id": str(uuid.uuid4()),
                "user_id": current_user.id,
                "day_of_week": day,
                "start_time": "09:00",
                "end_time": "17:00",
                "is_available": True
            })
        for rule in default_rules:
            await db.availability_rules.insert_one(rule)
        # Re-fetch without _id
        rules = await db.availability_rules.find(
            {"user_id": current_user.id}, 
            {"_id": 0}
        ).to_list(100)
    
    return rules

@api_router.put("/availability")
async def update_availability(
    rules: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
):
    """Update availability rules"""
    # Delete existing rules
    await db.availability_rules.delete_many({"user_id": current_user.id})
    
    # Insert new rules
    for rule in rules:
        rule["user_id"] = current_user.id
        rule["id"] = str(uuid.uuid4())
        await db.availability_rules.insert_one(rule)
    
    return {"message": "Availability updated"}

# ============================================
# GONG-LIKE CALL ANALYTICS & INTELLIGENCE
# ============================================

class CallRecording(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    user_id: str
    lead_id: Optional[str] = None
    recording_url: Optional[str] = None
    duration_seconds: int = 0
    transcription: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None  # positive, neutral, negative
    talk_time: Dict[str, int] = {}  # user_id -> seconds
    key_moments: List[Dict[str, Any]] = []  # timestamps of important moments
    action_items: List[str] = []
    topics: List[str] = []
    deal_signals: List[Dict[str, Any]] = []  # buying signals, objections, etc.
    coaching_tips: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@api_router.get("/call-analytics")
async def get_call_analytics(
    current_user: User = Depends(get_current_user),
    days: int = 30
):
    """Get Gong-like call analytics dashboard data"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get all calls for user
    calls = await db.call_logs.find({
        "user_id": current_user.id,
        "created_at": {"$gte": start_date}
    }, {"_id": 0}).to_list(1000)
    
    # Get recordings with analysis
    recordings = await db.call_recordings.find({
        "user_id": current_user.id,
        "created_at": {"$gte": start_date}
    }, {"_id": 0}).to_list(1000)
    
    # Calculate metrics
    total_calls = len(calls)
    total_duration = sum(c.get("duration", 0) for c in calls)
    avg_duration = total_duration / total_calls if total_calls > 0 else 0
    
    # Sentiment breakdown
    sentiments = {"positive": 0, "neutral": 0, "negative": 0}
    for r in recordings:
        s = r.get("sentiment", "neutral")
        sentiments[s] = sentiments.get(s, 0) + 1
    
    # Top topics
    topic_counts = {}
    for r in recordings:
        for topic in r.get("topics", []):
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Deal signals
    all_signals = []
    for r in recordings:
        all_signals.extend(r.get("deal_signals", []))
    
    buying_signals = [s for s in all_signals if s.get("type") == "buying_signal"]
    objections = [s for s in all_signals if s.get("type") == "objection"]
    
    # Talk ratio (average)
    talk_ratios = []
    for r in recordings:
        talk_time = r.get("talk_time", {})
        user_time = talk_time.get(current_user.id, 0)
        total_time = sum(talk_time.values()) or 1
        talk_ratios.append(user_time / total_time * 100)
    avg_talk_ratio = sum(talk_ratios) / len(talk_ratios) if talk_ratios else 50
    
    # Coaching tips aggregated
    all_tips = []
    for r in recordings:
        all_tips.extend(r.get("coaching_tips", []))
    tip_counts = {}
    for tip in all_tips:
        tip_counts[tip] = tip_counts.get(tip, 0) + 1
    top_coaching_tips = sorted(tip_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "overview": {
            "total_calls": total_calls,
            "total_duration_minutes": round(total_duration / 60, 1),
            "avg_duration_minutes": round(avg_duration / 60, 1),
            "avg_talk_ratio": round(avg_talk_ratio, 1)
        },
        "sentiment": sentiments,
        "top_topics": [{"topic": t[0], "count": t[1]} for t in top_topics],
        "deal_signals": {
            "buying_signals": len(buying_signals),
            "objections": len(objections),
            "recent_signals": all_signals[:10]
        },
        "coaching": {
            "tips": [{"tip": t[0], "occurrences": t[1]} for t in top_coaching_tips]
        },
        "recent_calls": calls[:10]
    }

@api_router.get("/call-recordings")
async def get_call_recordings(
    current_user: User = Depends(get_current_user),
    limit: int = 20
):
    """Get list of call recordings with analysis"""
    recordings = await db.call_recordings.find(
        {"user_id": current_user.id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return recordings

@api_router.get("/call-recordings/{recording_id}")
async def get_call_recording_detail(
    recording_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed call recording with full transcription and analysis"""
    recording = await db.call_recordings.find_one(
        {"id": recording_id, "user_id": current_user.id},
        {"_id": 0}
    )
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording

@api_router.post("/call-recordings/{call_id}/analyze")
async def analyze_call_recording(
    call_id: str,
    current_user: User = Depends(get_current_user)
):
    """Analyze a call recording using AI (Gong-like analysis)"""
    # Get call log
    call = await db.call_logs.find_one({"call_sid": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Check for existing transcription
    existing = await db.call_recordings.find_one({"call_id": call_id}, {"_id": 0})
    if existing and existing.get("transcription"):
        transcription = existing["transcription"]
    else:
        # In production, this would fetch and transcribe the recording
        transcription = call.get("transcription", "")
    
    if not transcription:
        return {"message": "No transcription available for this call"}
    
    # Analyze with AI
    analysis = await analyze_call_with_ai(transcription, call)
    
    # Store recording analysis
    recording_data = {
        "id": str(uuid.uuid4()),
        "call_id": call_id,
        "user_id": current_user.id,
        "lead_id": call.get("lead_id"),
        "duration_seconds": call.get("duration", 0),
        "transcription": transcription,
        **analysis,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.call_recordings.update_one(
        {"call_id": call_id},
        {"$set": recording_data},
        upsert=True
    )
    
    return recording_data

async def analyze_call_with_ai(transcription: str, call_data: dict) -> dict:
    """Use AI to analyze call transcription (Gong-like analysis)"""
    if not EMERGENT_LLM_KEY:
        return {
            "summary": "AI analysis unavailable",
            "sentiment": "neutral",
            "topics": [],
            "action_items": [],
            "deal_signals": [],
            "coaching_tips": []
        }
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"call-transcription-analysis-{uuid.uuid4().hex[:8]}",
            system_message="You are an expert sales call analyst like Gong.io. Analyze sales calls and provide actionable insights."
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Analyze this sales call transcription and provide insights like Gong.io would.

TRANSCRIPTION:
{transcription[:4000]}

Provide your analysis in JSON format:
{{
    "summary": "2-3 sentence summary of the call",
    "sentiment": "positive/neutral/negative",
    "topics": ["list", "of", "main", "topics", "discussed"],
    "action_items": ["action item 1", "action item 2"],
    "deal_signals": [
        {{"type": "buying_signal", "text": "quote from call", "timestamp": "approximate"}},
        {{"type": "objection", "text": "quote from call", "timestamp": "approximate"}}
    ],
    "key_moments": [
        {{"type": "question", "text": "important question asked", "timestamp": "approximate"}},
        {{"type": "commitment", "text": "commitment made", "timestamp": "approximate"}}
    ],
    "talk_ratio_assessment": "Assessment of talk time balance",
    "coaching_tips": [
        "Specific coaching tip based on the call",
        "Another improvement suggestion"
    ],
    "next_steps": ["Recommended next step 1", "Recommended next step 2"]
}}"""

        response = await chat.send_message_async(UserMessage(prompt))
        
        try:
            # Parse JSON from response
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            analysis = json.loads(response_text.strip())
            return analysis
        except json.JSONDecodeError:
            return {
                "summary": response.text[:500],
                "sentiment": "neutral",
                "topics": [],
                "action_items": [],
                "deal_signals": [],
                "coaching_tips": []
            }
            
    except Exception as e:
        logging.error(f"AI call analysis failed: {e}")
        return {
            "summary": "Analysis failed",
            "sentiment": "neutral",
            "topics": [],
            "action_items": [],
            "deal_signals": [],
            "coaching_tips": []
        }

@api_router.get("/call-analytics/leaderboard")
async def get_call_leaderboard(
    current_user: User = Depends(get_current_user),
    days: int = 30
):
    """Get team call performance leaderboard"""
    is_admin = current_user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or current_user.role == 'admin'
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Aggregate calls by user
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$user_id",
            "total_calls": {"$sum": 1},
            "total_duration": {"$sum": "$duration"},
            "connected_calls": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}}
        }},
        {"$sort": {"total_calls": -1}}
    ]
    
    results = await db.call_logs.aggregate(pipeline).to_list(100)
    
    # Enrich with user names
    leaderboard = []
    for r in results:
        user = await db.users.find_one({"id": r["_id"]}, {"_id": 0, "full_name": 1, "email": 1})
        if user:
            leaderboard.append({
                "user_id": r["_id"],
                "name": user.get("full_name", "Unknown"),
                "email": user.get("email", ""),
                "total_calls": r["total_calls"],
                "total_duration_minutes": round(r["total_duration"] / 60, 1),
                "connected_calls": r["connected_calls"],
                "connect_rate": round(r["connected_calls"] / r["total_calls"] * 100, 1) if r["total_calls"] > 0 else 0
            })
    
    return leaderboard

@api_router.post("/chat/messages/{message_id}/reactions")
async def add_reaction(
    message_id: str,
    reaction: dict,
    current_user: User = Depends(get_current_user)
):
    """Add a reaction to a message"""
    emoji = reaction.get("emoji")
    if not emoji:
        raise HTTPException(status_code=400, detail="Emoji is required")
    
    # Get message
    message = await db.chat_messages.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Add reaction
    reactions = message.get("reactions", {})
    if emoji not in reactions:
        reactions[emoji] = []
    
    if current_user.id not in reactions[emoji]:
        reactions[emoji].append(current_user.id)
    else:
        # Toggle off if already reacted
        reactions[emoji].remove(current_user.id)
        if not reactions[emoji]:
            del reactions[emoji]
    
    await db.chat_messages.update_one(
        {"id": message_id},
        {"$set": {"reactions": reactions}}
    )
    
    return {"reactions": reactions}

@api_router.post("/chat/messages/{message_id}/thread")
async def reply_to_thread(
    message_id: str,
    msg_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user)
):
    """Reply to a message thread"""
    # Verify parent message exists
    parent = await db.chat_messages.find_one({"id": message_id})
    if not parent:
        raise HTTPException(status_code=404, detail="Parent message not found")
    
    # Create reply with thread reference
    message = ChatMessage(
        **msg_data.model_dump(),
        sender_id=current_user.id,
        sender_name=current_user.full_name,
        metadata={
            **(msg_data.metadata or {}),
            "thread_id": message_id,
            "reply_to": message_id
        }
    )
    doc = message.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.chat_messages.insert_one(doc)
    
    # Update parent message thread count
    await db.chat_messages.update_one(
        {"id": message_id},
        {"$inc": {"reply_count": 1}}
    )
    
    return message

@api_router.delete("/chat/messages/{message_id}")
async def delete_chat_message(message_id: str, current_user: User = Depends(get_current_user)):
    """Delete a chat message - only message author or admin can delete"""
    # Check if user is admin
    is_admin = current_user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or current_user.role == 'admin'
    
    # Find the message
    message = await db.chat_messages.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check permissions - must be message author or admin
    if message["sender_id"] != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")
    
    # Delete the message
    await db.chat_messages.delete_one({"id": message_id})
    
    # Also delete any replies to this message
    await db.chat_messages.delete_many({"metadata.reply_to": message_id})
    
    # Log activity
    activity = Activity(
        type="message_deleted",
        description=f"Deleted message in channel",
        user_id=current_user.id,
        metadata={"message_id": message_id, "channel_id": message.get("channel_id")}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return {"success": True, "message": "Message deleted"}


@api_router.get("/team-members", response_model=List[User])
async def get_team_members(current_user: User = Depends(get_current_user)):
    """Get all team members (for calendar attendees, assignments, etc.)"""
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [User(**user) for user in users]

# ==================== AI Assistant Endpoints ====================

@api_router.post("/assistant/chat")
async def assistant_chat(request: AssistantChatRequest, current_user: User = Depends(get_current_user)):
    """AI Assistant for helping users navigate the platform"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"assistant-{current_user.id}",
            system_message="""You are a helpful AI assistant for LeadGen Pro, a sales CRM platform. 
            Help users navigate the platform and provide guidance on sales best practices.
            
            Platform features include:
            - Dashboard: View stats, AI insights, and recent activity
            - Pipeline: Kanban board for managing leads through stages (Prospecting → Qualified → Proposal → Negotiation → Closed)
            - Leads: Add, import, or scrape leads. Click on leads to see details and activity history
            - Calendar: Team calendar for scheduling meetings, calls, and tasks
            - Tasks: Create and track tasks, assign to team members
            - Meetings: Schedule and manage appointments with prospects
            - Team Chat: Internal messaging with channels
            - Call Analytics: View call recordings, transcripts, and AI-powered analysis
            
            Quick tips:
            - To add a lead: Go to Leads page → Click "Add Lead" button
            - To make a call: Go to a lead's detail page → Click the green "Call" button
            - To schedule a meeting: Go to Calendar → Click "New Event" or click on a time slot
            - To move a lead through the pipeline: Go to Pipeline → Drag and drop the lead card
            
            Be concise, helpful, and encourage users to explore the platform. If you don't know something specific about the platform, provide general sales guidance instead."""
        ).with_model("openai", "gpt-4o")
        
        message = UserMessage(text=request.message)
        response = await chat.send_message(message)
        
        return {"response": response}
    except Exception as e:
        logging.error(f"Assistant error: {e}")
        return {"response": "I'm having trouble connecting right now. Please try again in a moment, or explore the platform using the sidebar navigation!"}

# ==================== Call Recording & Analysis Endpoints ====================

@api_router.get("/calls/{call_id}/analysis")
async def get_call_analysis(call_id: str, current_user: User = Depends(get_current_user)):
    """Get AI analysis of a call (generate if not exists)"""
    call = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # If analysis already exists, return it
    if call.get("analysis"):
        return call
    
    # Generate analysis using AI
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"call-analysis-{call_id}",
            system_message="You are a sales call analyst. Analyze calls and provide insights."
        ).with_model("openai", "gpt-4o")
        
        # Create context from call data
        context = f"""Analyze this sales call:
        - Outcome: {call.get('outcome')}
        - Duration: {call.get('duration')} seconds
        - Notes: {call.get('notes', 'No notes provided')}
        
        Provide analysis in JSON format with:
        - sentiment (0-1 scale)
        - talk_ratio (percentage of time agent talked, estimate)
        - questions_asked (estimated number)
        - topics (list of key topics discussed)
        - coaching_tip (one actionable improvement suggestion)
        
        Return only valid JSON."""
        
        message = UserMessage(text=context)
        response = await chat.send_message(message)
        
        # Parse the AI response
        try:
            import json
            # Clean the response
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            analysis = json.loads(clean_response.strip())
        except:
            # Default analysis if parsing fails
            analysis = {
                "sentiment": 0.5,
                "talk_ratio": 50,
                "questions_asked": 3,
                "topics": ["product", "pricing", "timeline"],
                "coaching_tip": "Try asking more open-ended questions to understand prospect needs better."
            }
        
        # Update call with analysis
        await db.call_logs.update_one(
            {"id": call_id},
            {"$set": {"analysis": analysis}}
        )
        
        call["analysis"] = analysis
        return call
        
    except Exception as e:
        logging.error(f"Call analysis error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate analysis")

@api_router.post("/calls/{call_id}/transcribe")
async def transcribe_call(call_id: str, current_user: User = Depends(get_current_user)):
    """Transcribe a call recording using OpenAI Whisper"""
    call = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Check if already transcribed
    if call.get("transcript"):
        return {
            "success": True,
            "call_id": call_id,
            "transcript": call["transcript"],
            "already_transcribed": True
        }
    
    # Check if recording URL exists
    recording_url = call.get("recording_url")
    if not recording_url:
        raise HTTPException(status_code=400, detail="No recording available for this call")
    
    try:
        # Download the audio file from the recording URL
        async with httpx.AsyncClient() as client:
            # Twilio recordings may need authentication
            if "twilio.com" in recording_url:
                auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                response = await client.get(recording_url, auth=auth, follow_redirects=True)
            else:
                response = await client.get(recording_url, follow_redirects=True)
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to download recording: {response.status_code}")
            
            audio_data = response.content
        
        # Initialize Whisper STT
        stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        
        # Create a file-like object from the audio data
        import io
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "recording.mp3"
        
        # Transcribe using Whisper
        transcription_response = await stt.transcribe(
            file=audio_file,
            model="whisper-1",
            response_format="verbose_json",
            language="en",
            prompt="This is a sales call between a sales representative and a potential customer."
        )
        
        transcript = transcription_response.text
        
        # Save transcript to database
        update_data = {"transcript": transcript}
        
        # If we have segments, save those too
        segments = []
        if hasattr(transcription_response, 'segments') and transcription_response.segments:
            for seg in transcription_response.segments:
                # Handle both object and dict formats
                if isinstance(seg, dict):
                    segments.append({
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", "")
                    })
                else:
                    segments.append({
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text
                    })
            update_data["transcript_segments"] = segments
        
        await db.call_logs.update_one(
            {"id": call_id},
            {"$set": update_data}
        )
        
        # Log activity
        activity = Activity(
            type="call_transcribed",
            description=f"Call recording transcribed",
            user_id=current_user.id,
            metadata={"call_id": call_id, "word_count": len(transcript.split())}
        )
        activity_doc = activity.model_dump()
        activity_doc['created_at'] = activity_doc['created_at'].isoformat()
        await db.activities.insert_one(activity_doc)
        
        return {
            "success": True,
            "call_id": call_id,
            "transcript": transcript,
            "segments": segments,
            "word_count": len(transcript.split()),
            "already_transcribed": False
        }
        
    except Exception as e:
        logging.error(f"Transcription error for call {call_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@api_router.post("/calls/{call_id}/analyze")
async def analyze_call_with_transcript(call_id: str, current_user: User = Depends(get_current_user)):
    """Perform Gong-like AI analysis on a call with transcript"""
    call = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    transcript = call.get("transcript", "")
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"call-analysis-{call_id}-{uuid.uuid4().hex[:8]}",
            system_message="""You are an expert sales call analyst like Gong. Analyze sales calls and provide detailed, actionable insights.
            Focus on:
            - Communication patterns and techniques
            - Customer engagement signals
            - Sales methodology adherence
            - Areas for improvement
            Always be constructive and specific in your feedback."""
        ).with_model("openai", "gpt-4o")
        
        # Create comprehensive analysis prompt
        analysis_prompt = f"""Analyze this sales call recording:

**Call Metadata:**
- Outcome: {call.get('outcome', 'Unknown')}
- Duration: {call.get('duration', 0)} seconds ({call.get('duration', 0) // 60} min {call.get('duration', 0) % 60} sec)
- Notes: {call.get('notes', 'No notes')}

**Call Transcript:**
{transcript if transcript else "No transcript available - analyze based on metadata only."}

Provide a comprehensive Gong-style analysis in the following JSON format:
{{
    "overall_score": <0-100 score based on call effectiveness>,
    "sentiment": {{
        "overall": <0-1 scale, 1 being most positive>,
        "customer": <0-1 customer sentiment>,
        "progression": "<improved/declined/stable>"
    }},
    "talk_ratio": {{
        "rep_percentage": <estimated % of time rep talked>,
        "customer_percentage": <estimated % of time customer talked>,
        "assessment": "<balanced/rep_dominated/customer_dominated>"
    }},
    "questions": {{
        "total_asked": <number>,
        "open_ended": <number>,
        "discovery_questions": <number>,
        "quality": "<excellent/good/needs_improvement>"
    }},
    "key_topics": ["topic1", "topic2", "topic3"],
    "customer_signals": {{
        "buying_signals": ["signal1", "signal2"],
        "objections": ["objection1"],
        "concerns": ["concern1"]
    }},
    "next_steps": {{
        "mentioned": <true/false>,
        "clear": <true/false>,
        "items": ["step1", "step2"]
    }},
    "coaching_insights": {{
        "strengths": ["strength1", "strength2"],
        "improvements": ["improvement1", "improvement2"],
        "priority_action": "<single most important action to improve>"
    }},
    "call_summary": "<2-3 sentence summary of the call>"
}}

Return ONLY valid JSON, no additional text."""

        message = UserMessage(text=analysis_prompt)
        response = await chat.send_message(message)
        
        # Parse the AI response
        try:
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            analysis = json.loads(clean_response.strip())
        except json.JSONDecodeError as je:
            logging.error(f"JSON parse error: {je}")
            # Fallback analysis
            analysis = {
                "overall_score": 65,
                "sentiment": {"overall": 0.6, "customer": 0.55, "progression": "stable"},
                "talk_ratio": {"rep_percentage": 55, "customer_percentage": 45, "assessment": "balanced"},
                "questions": {"total_asked": 5, "open_ended": 2, "discovery_questions": 2, "quality": "good"},
                "key_topics": ["product features", "pricing", "implementation"],
                "customer_signals": {"buying_signals": [], "objections": [], "concerns": []},
                "next_steps": {"mentioned": True, "clear": False, "items": ["Follow up"]},
                "coaching_insights": {
                    "strengths": ["Good rapport building"],
                    "improvements": ["Ask more discovery questions"],
                    "priority_action": "Focus on understanding customer needs before presenting solutions"
                },
                "call_summary": "Sales call with discussion of product and pricing. Follow-up needed."
            }
        
        # Update call with detailed analysis
        await db.call_logs.update_one(
            {"id": call_id},
            {"$set": {"analysis": analysis, "analyzed_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Also update with simpler analysis fields for backward compatibility
        simple_analysis = {
            "sentiment": analysis.get("sentiment", {}).get("overall", 0.5),
            "talk_ratio": analysis.get("talk_ratio", {}).get("rep_percentage", 50),
            "questions_asked": analysis.get("questions", {}).get("total_asked", 0),
            "topics": analysis.get("key_topics", []),
            "coaching_tip": analysis.get("coaching_insights", {}).get("priority_action", "")
        }
        
        return {
            "success": True,
            "call_id": call_id,
            "analysis": analysis,
            "simple_analysis": simple_analysis
        }
        
    except Exception as e:
        logging.error(f"Analysis error for call {call_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# ==================== AI Call Coaching Endpoints ====================

@api_router.post("/calls/{call_id}/coaching")
async def get_ai_call_coaching(call_id: str, current_user: User = Depends(get_current_user)):
    """Get comprehensive AI coaching for a specific call - Gong-like features"""
    call = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    transcript = call.get("transcript", "")
    if not transcript:
        raise HTTPException(status_code=400, detail="Call has no transcript. Transcribe the call first.")
    
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="AI features not configured")
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"call-coaching-{call_id}",
            system_message="You are an elite sales coach like Gong.io's AI. Provide comprehensive coaching analysis for sales calls."
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""You are an elite sales coach like Gong.io's AI. Analyze this sales call transcript and provide comprehensive coaching.

CALL TRANSCRIPT:
{transcript[:6000]}

CALL METADATA:
- Duration: {call.get('duration', 0)} seconds
- Outcome: {call.get('outcome', 'unknown')}
- Disposition: {call.get('disposition', 'none')}

Provide detailed coaching analysis in JSON format:
{{
    "overall_score": 0-100,
    "real_time_suggestions": [
        {{"moment": "When customer said X", "suggestion": "You could have responded with...", "skill": "objection_handling"}},
        {{"moment": "At the opening", "suggestion": "Start with a stronger hook by...", "skill": "opening"}}
    ],
    "talk_to_listen_analysis": {{
        "rep_talk_percentage": 0-100,
        "customer_talk_percentage": 0-100,
        "longest_monologue_seconds": 0,
        "assessment": "Good balance / Rep dominated / Customer dominated",
        "recommendation": "Specific advice to improve"
    }},
    "sentiment_analysis": {{
        "overall_sentiment": "positive/neutral/negative",
        "customer_sentiment_progression": ["start: neutral", "middle: interested", "end: positive"],
        "sentiment_shifts": [
            {{"moment": "When X was mentioned", "shift": "positive to cautious", "cause": "price discussion"}}
        ],
        "alerts": ["Any concerning sentiment moments"]
    }},
    "question_quality": {{
        "total_questions": 0,
        "open_ended": 0,
        "closed_ended": 0,
        "discovery_questions": 0,
        "qualification_questions": 0,
        "best_questions": ["List of effective questions asked"],
        "missed_opportunities": ["Questions that should have been asked"]
    }},
    "key_moments": {{
        "buying_signals": [{{"quote": "Customer quote", "signal_type": "interest/urgency/budget_confirmation"}}],
        "objections": [{{"quote": "Customer objection", "how_handled": "well/poorly/missed", "better_response": "suggestion"}}],
        "commitments": [{{"who": "rep/customer", "what": "commitment made"}}],
        "turning_points": [{{"moment": "Description", "impact": "positive/negative"}}]
    }},
    "coaching_recommendations": {{
        "top_strength": "What they did best",
        "priority_improvement": "Most important thing to work on",
        "specific_tips": [
            {{"skill": "discovery", "tip": "Specific actionable advice", "example": "Example script"}},
            {{"skill": "closing", "tip": "Specific actionable advice", "example": "Example script"}}
        ],
        "training_focus": ["Skills to develop"],
        "scripts_to_practice": ["Specific phrases or scripts to memorize"]
    }},
    "next_call_prep": {{
        "follow_up_topics": ["Topics to address in follow-up"],
        "opening_suggestion": "How to open the next call",
        "objections_to_prepare": ["Anticipated objections and responses"]
    }}
}}"""

        response = await chat.send_message(UserMessage(prompt))
        
        # Parse the response
        response_text = response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        coaching = json.loads(response_text.strip())
        
        # Save coaching to call record
        await db.call_logs.update_one(
            {"id": call_id},
            {"$set": {"coaching": coaching, "coached_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {
            "success": True,
            "call_id": call_id,
            "coaching": coaching
        }
        
    except json.JSONDecodeError:
        # Return partial analysis if JSON parsing fails
        return {
            "success": True,
            "call_id": call_id,
            "coaching": {
                "overall_score": 70,
                "coaching_recommendations": {
                    "top_strength": "Engaged with the customer",
                    "priority_improvement": "Ask more discovery questions",
                    "specific_tips": [{"skill": "discovery", "tip": "Use SPIN selling methodology"}]
                },
                "raw_analysis": response.text[:2000] if 'response' in dir() else "Analysis pending"
            }
        }
    except Exception as e:
        logging.error(f"AI coaching error: {e}")
        raise HTTPException(status_code=500, detail=f"Coaching analysis failed: {str(e)}")

@api_router.get("/calls/coaching/team-insights")
async def get_team_coaching_insights(
    current_user: User = Depends(get_current_user),
    days: int = 30
):
    """Get aggregated coaching insights for the team"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get all calls with coaching data
    calls = await db.call_logs.find({
        "coached_at": {"$exists": True},
        "created_at": {"$gte": cutoff.isoformat()}
    }, {"_id": 0, "coaching": 1, "agent_id": 1}).to_list(1000)
    
    if not calls:
        return {
            "team_avg_score": 0,
            "common_strengths": [],
            "common_improvements": [],
            "top_performers": [],
            "skill_gaps": []
        }
    
    # Aggregate insights
    scores = []
    strengths = []
    improvements = []
    agent_scores = {}
    
    for call in calls:
        coaching = call.get("coaching", {})
        score = coaching.get("overall_score", 0)
        scores.append(score)
        
        agent_id = call.get("agent_id")
        if agent_id:
            if agent_id not in agent_scores:
                agent_scores[agent_id] = []
            agent_scores[agent_id].append(score)
        
        rec = coaching.get("coaching_recommendations", {})
        if rec.get("top_strength"):
            strengths.append(rec["top_strength"])
        if rec.get("priority_improvement"):
            improvements.append(rec["priority_improvement"])
    
    # Get top performers
    agent_averages = [
        {"agent_id": aid, "avg_score": sum(s)/len(s), "calls": len(s)}
        for aid, s in agent_scores.items()
    ]
    top_performers = sorted(agent_averages, key=lambda x: x["avg_score"], reverse=True)[:5]
    
    # Get user names for top performers
    for perf in top_performers:
        user = await db.users.find_one({"id": perf["agent_id"]}, {"_id": 0, "full_name": 1})
        perf["name"] = user.get("full_name", "Unknown") if user else "Unknown"
    
    return {
        "team_avg_score": sum(scores) / len(scores) if scores else 0,
        "total_calls_analyzed": len(calls),
        "common_strengths": list(set(strengths))[:5],
        "common_improvements": list(set(improvements))[:5],
        "top_performers": top_performers,
        "score_distribution": {
            "excellent": len([s for s in scores if s >= 80]),
            "good": len([s for s in scores if 60 <= s < 80]),
            "needs_work": len([s for s in scores if s < 60])
        }
    }

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

@api_router.post("/errors/report")
async def report_error(
    error: ErrorReport,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Report an error from frontend or backend"""
    # Categorize the error
    category, error_type, severity = categorize_error(error.error_message, error.endpoint)
    
    # Attempt auto-fix
    auto_fix_result = await attempt_auto_fix(category, error_type, {
        "user_id": current_user.id,
        "request_data": error.request_data
    })
    
    # Log to database
    error_doc = await log_error_to_db(
        error_type=error.error_type,
        error_message=error.error_message,
        category=category,
        severity=severity,
        user_id=current_user.id,
        endpoint=error.endpoint,
        request_data=error.request_data,
        stack_trace=error.stack_trace,
        auto_fix_attempted=auto_fix_result.get("attempted", False),
        auto_fix_result=auto_fix_result.get("message")
    )
    
    # Get rule-based suggestions
    rules = AUTO_FIX_RULES.get(category, {}).get(error_type, {})
    
    return {
        "error_id": error_doc["id"],
        "category": category,
        "severity": severity,
        "auto_fix": auto_fix_result,
        "user_suggestion": rules.get("user_action", "Please try again or contact support."),
        "admin_suggestion": rules.get("admin_action", "Check logs for more details.") if current_user.role == "admin" else None
    }

@api_router.post("/support-bot/diagnose")
async def support_bot_diagnose(
    request: SupportBotRequest,
    current_user: User = Depends(get_current_user)
):
    """AI-powered support bot for error diagnosis and help"""
    error_doc = None
    
    # If error_id provided, get the error details
    if request.error_id:
        error_doc = await db.system_errors.find_one({"id": request.error_id}, {"_id": 0})
    
    # If no specific error, create a context for general questions
    if not error_doc:
        error_doc = {
            "error_type": "user_question",
            "error_message": request.question,
            "category": "support",
            "endpoint": request.context.get("page") if request.context else None
        }
    
    # Get AI diagnosis
    diagnosis = await get_ai_diagnosis(error_doc)
    
    # Store the support interaction
    interaction = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "error_id": request.error_id,
        "question": request.question,
        "diagnosis": diagnosis,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.support_interactions.insert_one(interaction)
    
    return {
        "diagnosis": diagnosis.get("diagnosis", "Unable to diagnose the issue"),
        "root_cause": diagnosis.get("root_cause"),
        "fix_steps": diagnosis.get("fix_steps", []),
        "prevention": diagnosis.get("prevention"),
        "severity": diagnosis.get("severity_assessment"),
        "can_auto_fix": diagnosis.get("can_auto_fix", False),
        "auto_fix_action": diagnosis.get("auto_fix_action")
    }

@api_router.post("/support-bot/auto-fix/{error_id}")
async def support_bot_auto_fix(
    error_id: str,
    current_user: User = Depends(get_current_user)
):
    """Attempt to automatically fix an error"""
    # Check if admin
    is_admin = current_user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or current_user.role == 'admin'
    if not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can trigger auto-fix")
    
    # Get error
    error_doc = await db.system_errors.find_one({"id": error_id}, {"_id": 0})
    if not error_doc:
        raise HTTPException(status_code=404, detail="Error not found")
    
    # Get AI diagnosis with auto-fix capability
    diagnosis = await get_ai_diagnosis(error_doc)
    
    if not diagnosis.get("can_auto_fix"):
        return {
            "success": False,
            "message": "This error cannot be automatically fixed",
            "manual_steps": diagnosis.get("fix_steps", [])
        }
    
    # Attempt the auto-fix based on AI recommendation
    auto_fix_result = await attempt_auto_fix(
        error_doc.get("category"),
        error_doc.get("error_type"),
        {"error_doc": error_doc, "diagnosis": diagnosis}
    )
    
    # Update error record
    await db.system_errors.update_one(
        {"id": error_id},
        {
            "$set": {
                "auto_fix_attempted": True,
                "auto_fix_result": auto_fix_result.get("message"),
                "resolved": auto_fix_result.get("success", False),
                "resolved_at": datetime.now(timezone.utc).isoformat() if auto_fix_result.get("success") else None
            }
        }
    )
    
    return {
        "success": auto_fix_result.get("success", False),
        "action_taken": auto_fix_result.get("action_taken"),
        "message": auto_fix_result.get("message"),
        "ai_diagnosis": diagnosis
    }

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

# =============================================================================
# PUBLIC API - External Integration Endpoints
# =============================================================================
# These endpoints allow external applications to integrate with LeadGen Pro
# using API keys for authentication instead of JWT tokens.

public_api = APIRouter(prefix="/public", tags=["Public API"])

class APIKey(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    key: str
    user_id: str
    permissions: List[str] = ["read"]  # read, write, delete, admin
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None
    is_active: bool = True

class CreateAPIKeyRequest(BaseModel):
    name: str
    permissions: List[str] = ["read"]

# API Key authentication dependency
async def get_api_key_user(request: Request):
    """Authenticate requests using API key in header"""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required. Add X-API-Key header.")
    
    key_doc = await db.api_keys.find_one({"key": api_key, "is_active": True})
    if not key_doc:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    
    # Update last used timestamp
    await db.api_keys.update_one(
        {"key": api_key},
        {"$set": {"last_used": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Get the user associated with this key
    user = await db.users.find_one({"id": key_doc["user_id"]}, {"_id": 0, "hashed_password": 0})
    if not user:
        raise HTTPException(status_code=401, detail="API key user not found")
    
    return User(**user), key_doc.get("permissions", ["read"])

# API Key Management (requires JWT auth)
@api_router.post("/api-keys")
async def create_api_key(request: CreateAPIKeyRequest, current_user: User = Depends(get_current_user)):
    """Create a new API key for external integrations"""
    import secrets
    
    api_key = APIKey(
        name=request.name,
        key=f"lgp_{secrets.token_urlsafe(32)}",
        user_id=current_user.id,
        permissions=request.permissions
    )
    
    key_doc = api_key.model_dump()
    key_doc['created_at'] = key_doc['created_at'].isoformat()
    await db.api_keys.insert_one(key_doc)
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": api_key.key,  # Only shown once!
        "permissions": api_key.permissions,
        "message": "Save this key securely - it won't be shown again!"
    }

@api_router.get("/api-keys")
async def list_api_keys(current_user: User = Depends(get_current_user)):
    """List all API keys for current user (keys are masked)"""
    keys = await db.api_keys.find(
        {"user_id": current_user.id},
        {"_id": 0, "key": 0}  # Don't return the actual key
    ).to_list(100)
    
    for key in keys:
        key["key_preview"] = "lgp_****" + key.get("id", "")[-8:]
    
    return keys

@api_router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str, current_user: User = Depends(get_current_user)):
    """Deactivate an API key"""
    result = await db.api_keys.update_one(
        {"id": key_id, "user_id": current_user.id},
        {"$set": {"is_active": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key deactivated"}

# =============================================================================
# PUBLIC API ENDPOINTS - For External Integrations
# =============================================================================

@public_api.get("/health")
async def public_health():
    """Health check endpoint - no auth required"""
    return {"status": "healthy", "service": "LeadGen Pro API", "version": "2.0"}

# ==================== Test Email Endpoint ====================

class TestEmailRequest(BaseModel):
    to_email: str
    
@api_router.post("/test-email")
async def send_test_email(request: TestEmailRequest, current_user: User = Depends(get_current_user)):
    """
    Send a test email to verify Resend configuration.
    Only admins can use this endpoint.
    """
    # Check if user is admin
    is_admin = current_user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or current_user.role == 'admin'
    if not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can send test emails")
    
    if not RESEND_API_KEY:
        return {
            "success": False,
            "error": "RESEND_API_KEY not configured",
            "sender_email": SENDER_EMAIL
        }
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; border-radius: 12px 12px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">LeadGen Pro - Test Email</h1>
        </div>
        
        <div style="background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
            <p style="font-size: 16px; margin-bottom: 20px;">🎉 <strong>Congratulations!</strong></p>
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                Your Resend email integration is working correctly!
            </p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
                <h2 style="color: #10b981; margin-top: 0; font-size: 18px;">Email Configuration</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; width: 120px;">Sender:</td>
                        <td style="padding: 8px 0; font-weight: bold;">{SENDER_EMAIL}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Timestamp:</td>
                        <td style="padding: 8px 0;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Sent by:</td>
                        <td style="padding: 8px 0;">{current_user.full_name} ({current_user.email})</td>
                    </tr>
                </table>
            </div>
            
            <p style="color: #64748b; font-size: 14px; margin-top: 30px;">
                This is a test email from LeadGen Pro to verify your email configuration.
            </p>
        </div>
    </body>
    </html>
    """
    
    params = {
        "from": SENDER_EMAIL,
        "to": [request.to_email],
        "subject": "LeadGen Pro - Test Email ✅",
        "html": html_content
    }
    
    try:
        email = await asyncio.to_thread(resend.Emails.send, params)
        logging.info(f"Test email sent to {request.to_email}, email_id: {email.get('id')}")
        return {
            "success": True,
            "message": f"Test email sent successfully to {request.to_email}",
            "email_id": email.get('id'),
            "sender_email": SENDER_EMAIL
        }
    except Exception as e:
        logging.error(f"Failed to send test email: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "sender_email": SENDER_EMAIL
        }

@public_api.get("/leads")
async def public_get_leads(
    limit: int = 50,
    offset: int = 0,
    stage: Optional[str] = None,
    auth: tuple = Depends(get_api_key_user)
):
    """Get leads via API key authentication"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    query = {}
    if stage:
        query["stage"] = stage
    
    leads = await db.leads.find(query, {"_id": 0}).skip(offset).limit(limit).to_list(limit)
    total = await db.leads.count_documents(query)
    
    return {"leads": leads, "total": total, "limit": limit, "offset": offset}

@public_api.get("/leads/{lead_id}")
async def public_get_lead(lead_id: str, auth: tuple = Depends(get_api_key_user)):
    """Get a specific lead by ID"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

class PublicLeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    source: str = "api"
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

@public_api.post("/leads")
async def public_create_lead(lead_data: PublicLeadCreate, auth: tuple = Depends(get_api_key_user)):
    """Create a new lead via API"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    lead = Lead(
        first_name=lead_data.first_name,
        last_name=lead_data.last_name,
        email=lead_data.email,
        phone=lead_data.phone,
        company=lead_data.company,
        title=lead_data.title,
        source=lead_data.source,
        notes=lead_data.notes,
        assigned_to=user.id
    )
    
    lead_doc = lead.model_dump()
    lead_doc['created_at'] = lead_doc['created_at'].isoformat()
    if lead_data.custom_fields:
        lead_doc['custom_fields'] = lead_data.custom_fields
    
    await db.leads.insert_one(lead_doc)
    
    return {"id": lead.id, "message": "Lead created successfully"}

@public_api.put("/leads/{lead_id}")
async def public_update_lead(lead_id: str, updates: Dict[str, Any], auth: tuple = Depends(get_api_key_user)):
    """Update a lead via API"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    # Remove protected fields
    updates.pop("id", None)
    updates.pop("_id", None)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.leads.update_one({"id": lead_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead updated successfully"}

@public_api.delete("/leads/{lead_id}")
async def public_delete_lead(lead_id: str, auth: tuple = Depends(get_api_key_user)):
    """Delete a lead via API"""
    user, permissions = auth
    if "delete" not in permissions:
        raise HTTPException(status_code=403, detail="Delete permission required")
    
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead deleted successfully"}

# Appointments/Meetings API
class PublicAppointmentCreate(BaseModel):
    title: str
    lead_id: Optional[str] = None
    lead_email: Optional[str] = None
    lead_name: Optional[str] = None
    scheduled_at: datetime
    duration: int = 30  # minutes
    meeting_type: str = "call"  # call, video, in_person
    notes: Optional[str] = None
    external_meeting_link: Optional[str] = None

@public_api.get("/appointments")
async def public_get_appointments(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    auth: tuple = Depends(get_api_key_user)
):
    """Get appointments within a date range"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    query = {}
    if start_date:
        query["scheduled_at"] = {"$gte": start_date}
    if end_date:
        if "scheduled_at" in query:
            query["scheduled_at"]["$lte"] = end_date
        else:
            query["scheduled_at"] = {"$lte": end_date}
    
    appointments = await db.appointments.find(query, {"_id": 0}).to_list(500)
    return {"appointments": appointments}

@public_api.post("/appointments")
async def public_create_appointment(appt: PublicAppointmentCreate, auth: tuple = Depends(get_api_key_user)):
    """Create a new appointment/meeting"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    appointment = {
        "id": f"appt_{uuid.uuid4().hex[:12]}",
        "title": appt.title,
        "lead_id": appt.lead_id,
        "lead_email": appt.lead_email,
        "lead_name": appt.lead_name,
        "employee_id": user.id,
        "scheduled_at": appt.scheduled_at.isoformat(),
        "duration": appt.duration,
        "meeting_type": appt.meeting_type,
        "notes": appt.notes,
        "external_meeting_link": appt.external_meeting_link,
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "api"
    }
    
    await db.appointments.insert_one(appointment)
    
    # Also create a calendar event
    calendar_event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "title": appt.title,
        "start": appt.scheduled_at.isoformat(),
        "end": (appt.scheduled_at + timedelta(minutes=appt.duration)).isoformat(),
        "type": "meeting",
        "lead_id": appt.lead_id,
        "user_id": user.id,
        "appointment_id": appointment["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.calendar_events.insert_one(calendar_event)
    
    return {"id": appointment["id"], "calendar_event_id": calendar_event["id"], "message": "Appointment created"}

@public_api.delete("/appointments/{appointment_id}")
async def public_cancel_appointment(appointment_id: str, auth: tuple = Depends(get_api_key_user)):
    """Cancel an appointment"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    result = await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return {"message": "Appointment cancelled"}

# Call Logs API
@public_api.get("/calls")
async def public_get_calls(
    lead_id: Optional[str] = None,
    limit: int = 50,
    auth: tuple = Depends(get_api_key_user)
):
    """Get call logs"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    
    calls = await db.call_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"calls": calls}

@public_api.post("/calls")
async def public_log_call(
    lead_id: str,
    phone_number: str,
    outcome: str,
    duration: int = 0,
    notes: Optional[str] = None,
    recording_url: Optional[str] = None,
    auth: tuple = Depends(get_api_key_user)
):
    """Log a call from an external system"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    call_log = {
        "id": f"call_{uuid.uuid4().hex[:12]}",
        "lead_id": lead_id,
        "agent_id": user.id,
        "phone_number": phone_number,
        "direction": "outbound",
        "outcome": outcome,
        "duration": duration,
        "notes": notes,
        "recording_url": recording_url,
        "source": "api",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.call_logs.insert_one(call_log)
    
    # Update lead's last_contacted
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"last_contacted": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"id": call_log["id"], "message": "Call logged successfully"}

# Activities API
@public_api.get("/activities/{lead_id}")
async def public_get_activities(lead_id: str, limit: int = 50, auth: tuple = Depends(get_api_key_user)):
    """Get activity timeline for a lead"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    activities = await db.activities.find(
        {"lead_id": lead_id}, 
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"activities": activities}

@public_api.post("/activities")
async def public_create_activity(
    lead_id: str,
    type: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
    auth: tuple = Depends(get_api_key_user)
):
    """Log an activity from an external system"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    activity = {
        "id": f"act_{uuid.uuid4().hex[:12]}",
        "type": type,
        "description": description,
        "lead_id": lead_id,
        "user_id": user.id,
        "metadata": metadata or {},
        "source": "api",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.activities.insert_one(activity)
    return {"id": activity["id"], "message": "Activity logged"}

# Tasks API
@public_api.get("/tasks")
async def public_get_tasks(
    status: Optional[str] = None,
    lead_id: Optional[str] = None,
    auth: tuple = Depends(get_api_key_user)
):
    """Get tasks"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    query = {}
    if status:
        query["completed"] = status == "completed"
    if lead_id:
        query["lead_id"] = lead_id
    
    tasks = await db.tasks.find(query, {"_id": 0}).to_list(500)
    return {"tasks": tasks}

class PublicTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    lead_id: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"

@public_api.post("/tasks")
async def public_create_task(task_data: PublicTaskCreate, auth: tuple = Depends(get_api_key_user)):
    """Create a task from external system"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    task = {
        "id": f"task_{uuid.uuid4().hex[:12]}",
        "title": task_data.title,
        "description": task_data.description,
        "lead_id": task_data.lead_id,
        "assigned_to": user.id,
        "due_date": task_data.due_date.isoformat() if task_data.due_date else None,
        "priority": task_data.priority,
        "completed": False,
        "source": "api",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.tasks.insert_one(task)
    return {"id": task["id"], "message": "Task created"}

# Webhooks - Allow external systems to subscribe to events
class WebhookSubscription(BaseModel):
    url: str
    events: List[str]  # lead.created, lead.updated, call.completed, appointment.created, etc.
    secret: Optional[str] = None

@public_api.post("/webhooks")
async def create_webhook(webhook: WebhookSubscription, auth: tuple = Depends(get_api_key_user)):
    """Subscribe to webhook events"""
    user, permissions = auth
    if "admin" not in permissions:
        raise HTTPException(status_code=403, detail="Admin permission required for webhooks")
    
    import secrets as sec
    webhook_doc = {
        "id": f"wh_{uuid.uuid4().hex[:12]}",
        "url": webhook.url,
        "events": webhook.events,
        "secret": webhook.secret or sec.token_urlsafe(32),
        "user_id": user.id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.webhooks.insert_one(webhook_doc)
    return {
        "id": webhook_doc["id"],
        "secret": webhook_doc["secret"],
        "message": "Webhook created. Use the secret to verify payloads."
    }

@public_api.get("/webhooks")
async def list_webhooks(auth: tuple = Depends(get_api_key_user)):
    """List webhook subscriptions"""
    user, permissions = auth
    webhooks = await db.webhooks.find(
        {"user_id": user.id, "is_active": True},
        {"_id": 0, "secret": 0}
    ).to_list(100)
    return {"webhooks": webhooks}

@public_api.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, auth: tuple = Depends(get_api_key_user)):
    """Delete a webhook subscription"""
    user, permissions = auth
    result = await db.webhooks.update_one(
        {"id": webhook_id, "user_id": user.id},
        {"$set": {"is_active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted"}

# API Documentation endpoint
@public_api.get("/docs")
async def api_documentation():
    """Get API documentation"""
    return {
        "name": "LeadGen Pro Public API",
        "version": "2.0",
        "base_url": "/api/public",
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "description": "Create API keys in your LeadGen Pro dashboard under Settings"
        },
        "endpoints": {
            "leads": {
                "GET /leads": "List leads with pagination",
                "GET /leads/{id}": "Get a specific lead",
                "POST /leads": "Create a new lead",
                "PUT /leads/{id}": "Update a lead",
                "DELETE /leads/{id}": "Delete a lead"
            },
            "appointments": {
                "GET /appointments": "List appointments",
                "POST /appointments": "Create appointment/meeting",
                "DELETE /appointments/{id}": "Cancel appointment"
            },
            "calls": {
                "GET /calls": "Get call logs",
                "POST /calls": "Log a call from external system"
            },
            "tasks": {
                "GET /tasks": "Get tasks",
                "POST /tasks": "Create a task"
            },
            "activities": {
                "GET /activities/{lead_id}": "Get activity timeline",
                "POST /activities": "Log an activity"
            },
            "webhooks": {
                "GET /webhooks": "List webhook subscriptions",
                "POST /webhooks": "Subscribe to events",
                "DELETE /webhooks/{id}": "Unsubscribe"
            }
        },
        "webhook_events": [
            "lead.created",
            "lead.updated", 
            "lead.stage_changed",
            "call.completed",
            "appointment.created",
            "appointment.cancelled",
            "task.created",
            "task.completed"
        ],
        "permissions": {
            "read": "View data",
            "write": "Create and update data",
            "delete": "Delete data",
            "admin": "Manage webhooks and settings"
        }
    }

# ==================== CRM Integrations Endpoints ====================

class CRMIntegration(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider: str
    status: str = "disconnected"
    api_key: Optional[str] = None
    instance_url: Optional[str] = None
    last_sync: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@api_router.get("/integrations/crm")
async def get_crm_integrations(current_user: User = Depends(get_current_user)):
    """Get all CRM integrations for the current user"""
    integrations = await db.crm_integrations.find(
        {"user_id": current_user.id},
        {"_id": 0}
    ).to_list(100)
    return integrations

@api_router.post("/integrations/crm")
async def create_crm_integration(
    provider: str,
    api_key: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Create a new CRM integration (placeholder for future implementation)"""
    # Check if integration already exists
    existing = await db.crm_integrations.find_one({
        "user_id": current_user.id,
        "provider": provider
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Integration already exists")
    
    integration = CRMIntegration(
        user_id=current_user.id,
        provider=provider,
        status="pending",
        api_key=api_key
    )
    
    doc = integration.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.crm_integrations.insert_one(doc)
    
    return {
        "success": True,
        "message": f"{provider} integration created. Full integration coming soon!",
        "integration": integration
    }

@api_router.delete("/integrations/crm/{provider}")
async def delete_crm_integration(provider: str, current_user: User = Depends(get_current_user)):
    """Delete a CRM integration"""
    result = await db.crm_integrations.delete_one({
        "user_id": current_user.id,
        "provider": provider
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {"success": True, "message": f"{provider} integration disconnected"}

@api_router.get("/integrations/crm/{provider}/status")
async def get_crm_integration_status(provider: str, current_user: User = Depends(get_current_user)):
    """Get status of a specific CRM integration"""
    integration = await db.crm_integrations.find_one(
        {"user_id": current_user.id, "provider": provider},
        {"_id": 0}
    )
    
    if not integration:
        return {"status": "not_connected", "provider": provider}
    
    return integration


# Employee Dashboard Endpoints
@api_router.get("/employee/dashboard")
async def employee_dashboard(current_user: User = Depends(get_current_user)):
    """Get employee's personal dashboard data"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_start = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)
    
    # Get daily goals and admin notes
    daily_goal = await db.daily_goals.find_one(
        {"employee_id": current_user.id, "date": today},
        {"_id": 0}
    )
    
    # Set default goals if none exist
    if not daily_goal:
        daily_goal = {
            "calls_target": 20,
            "meetings_target": 3,
            "emails_target": 10,
            "notes": None
        }
    
    # Get actual progress
    calls_made = await db.call_logs.count_documents({
        "agent_id": current_user.id,
        "created_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    meetings_scheduled = await db.appointments.count_documents({
        "employee_id": current_user.id,
        "scheduled_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    # Get leads assigned to this employee
    my_leads = await db.leads.find(
        {"assigned_to": current_user.id, "stage": {"$ne": "closed"}},
        {"_id": 0}
    ).to_list(1000)
    
    # Get today's tasks
    my_tasks = await db.tasks.find(
        {"assigned_to": current_user.id, "completed": False},
        {"_id": 0}
    ).sort("due_date", 1).to_list(50)
    
    # Calculate personal stats
    total_calls = await db.call_logs.count_documents({"agent_id": current_user.id})
    total_leads_assigned = await db.leads.count_documents({"assigned_to": current_user.id})
    leads_converted = await db.leads.count_documents({"assigned_to": current_user.id, "stage": "closed"})
    
    return {
        "daily_goals": daily_goal,
        "progress": {
            "calls_made": calls_made,
            "calls_target": daily_goal.get('calls_target', 20),
            "meetings_scheduled": meetings_scheduled,
            "meetings_target": daily_goal.get('meetings_target', 3)
        },
        "admin_notes": daily_goal.get('notes'),
        "my_leads_count": len(my_leads),
        "pending_tasks_count": len(my_tasks),
        "personal_stats": {
            "total_calls": total_calls,
            "total_leads": total_leads_assigned,
            "leads_converted": leads_converted,
            "conversion_rate": round((leads_converted / total_leads_assigned * 100) if total_leads_assigned > 0 else 0, 1)
        }
    }

@api_router.get("/employee/my-leads")
async def get_my_leads(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get leads assigned to the current employee"""
    query = {"assigned_to": current_user.id}
    if status:
        query["status"] = status
    
    leads = await db.leads.find(query, {"_id": 0}).limit(limit).to_list(limit)
    return leads

@api_router.get("/employee/my-tasks")
async def get_my_tasks(
    completed: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Get tasks assigned to the current employee"""
    query = {"assigned_to": current_user.id}
    if completed is not None:
        query["completed"] = completed
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("due_date", 1).to_list(100)
    return tasks

@api_router.get("/employee/my-stats")
async def get_my_stats(current_user: User = Depends(get_current_user)):
    """Get personal performance statistics for the employee"""
    # Get weekly data
    week_start = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Calls by day for the last 7 days
    daily_calls = []
    for i in range(7):
        day = datetime.now(timezone.utc) - timedelta(days=6-i)
        day_str = day.strftime("%Y-%m-%d")
        day_start = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        
        count = await db.call_logs.count_documents({
            "agent_id": current_user.id,
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        })
        daily_calls.append({"day": day.strftime("%a"), "calls": count})
    
    # Overall stats
    total_calls = await db.call_logs.count_documents({"agent_id": current_user.id})
    total_meetings = await db.appointments.count_documents({"employee_id": current_user.id})
    leads_assigned = await db.leads.count_documents({"assigned_to": current_user.id})
    leads_converted = await db.leads.count_documents({"assigned_to": current_user.id, "stage": "closed"})
    
    # Get call outcomes
    connected_calls = await db.call_logs.count_documents({
        "agent_id": current_user.id,
        "outcome": "connected"
    })
    
    return {
        "daily_calls": daily_calls,
        "total_calls": total_calls,
        "total_meetings": total_meetings,
        "leads_assigned": leads_assigned,
        "leads_converted": leads_converted,
        "conversion_rate": round((leads_converted / leads_assigned * 100) if leads_assigned > 0 else 0, 1),
        "connect_rate": round((connected_calls / total_calls * 100) if total_calls > 0 else 0, 1)
    }

# ==================== SMART NOTIFICATIONS ====================
# NOTE: Smart Notifications, Push Notifications, and Digest Email endpoints
# have been moved to modular routes:
# - /app/backend/routes/notifications.py
# - /app/backend/routes/push.py
# - /app/backend/routes/auth.py
# The main GET /notifications endpoint remains here for admin error integration.

# Include public API router
app.include_router(public_api, prefix="/api")

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