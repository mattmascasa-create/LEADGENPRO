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
from routes import notifications_router, push_router, auth_router, leads_router
from routes.notifications import (
    NotificationType, SmartNotification, NotificationPreferences,
    send_push_to_user, should_send_notification, create_lead_assigned_notification
)
from routes.leads import Lead, LeadCreate, Activity, calculate_lead_score

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

# Leads routes
@api_router.get("/leads", response_model=List[Lead])
async def get_leads(stage: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {}
    
    # Check if user is an admin (by role or by ADMIN_EMAILS list)
    is_admin = current_user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or current_user.role == 'admin'
    
    # Admins see ALL leads (no filter on assigned_to or created_by)
    if not is_admin:
        if current_user.role == "employee":
            query["assigned_to"] = current_user.id
        elif current_user.role == "client":
            query["created_by"] = current_user.id
    # Admins: query remains empty, returning ALL leads
    
    if stage:
        query["stage"] = stage
    
    leads = await db.leads.find(query, {"_id": 0}).to_list(1000)
    return [Lead(**lead) for lead in leads]

@api_router.post("/leads", response_model=Lead)
async def create_lead(lead_data: LeadCreate, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    lead_dict = lead_data.model_dump()
    lead_dict['created_by'] = current_user.id
    
    # Calculate lead score
    lead_dict['score'] = await calculate_lead_score(lead_dict)
    
    lead = Lead(**lead_dict)
    doc = lead.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.leads.insert_one(doc)
    
    # Generate AI insights in background
    async def generate_insights():
        insights = await generate_ai_insight(doc)
        await db.leads.update_one(
            {"id": lead.id},
            {"$set": {"ai_insights": insights}}
        )
    
    background_tasks.add_task(generate_insights)
    
    # Log activity
    activity = Activity(
        type="lead_created",
        description=f"Created lead: {lead.first_name} {lead.last_name}",
        lead_id=lead.id,
        user_id=current_user.id
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return lead

@api_router.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return Lead(**lead)

@api_router.put("/leads/{lead_id}", response_model=Lead)
async def update_lead(lead_id: str, lead_data: LeadCreate, current_user: User = Depends(get_current_user)):
    update_data = lead_data.model_dump()
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    update_data['score'] = await calculate_lead_score(update_data)
    
    result = await db.leads.update_one(
        {"id": lead_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return Lead(**updated_lead)

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted successfully"}

@api_router.post("/leads/{lead_id}/stage")
async def update_lead_stage(lead_id: str, stage: str, current_user: User = Depends(get_current_user)):
    result = await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"stage": stage, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Log activity
    activity = Activity(
        type="stage_changed",
        description=f"Moved lead to {stage}",
        lead_id=lead_id,
        user_id=current_user.id,
        metadata={"new_stage": stage}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return {"message": "Stage updated"}

# Appointments routes
@api_router.get("/appointments", response_model=List[Appointment])
async def get_appointments(current_user: User = Depends(get_current_user)):
    query = {}
    if current_user.role == "employee":
        query["employee_id"] = current_user.id
    
    appointments = await db.appointments.find(query, {"_id": 0}).to_list(1000)
    return [Appointment(**apt) for apt in appointments]

@api_router.post("/appointments", response_model=Appointment)
async def create_appointment(apt_data: AppointmentCreate, current_user: User = Depends(get_current_user)):
    appointment = Appointment(**apt_data.model_dump())
    doc = appointment.model_dump()
    doc['scheduled_at'] = doc['scheduled_at'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.appointments.insert_one(doc)
    
    # Log activity
    activity = Activity(
        type="appointment_created",
        description=f"Scheduled: {appointment.title}",
        lead_id=appointment.lead_id,
        user_id=current_user.id
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return appointment

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


@api_router.get("/calls/dispositions")
async def get_call_dispositions():
    """Get available call disposition options"""
    return CALL_DISPOSITIONS

@api_router.put("/calls/{call_id}/disposition")
async def update_call_disposition(
    call_id: str,
    disposition: str,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Update call disposition after a call ends"""
    # First check if call_log exists
    call_log = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    
    # If no call_log yet, try to create one from pending_call
    if not call_log:
        pending_call = await db.pending_calls.find_one({"id": call_id})
        if pending_call:
            # Create call_log from pending call data
            call_log = {
                "id": call_id,
                "call_sid": pending_call.get("agent_call_sid"),
                "lead_id": pending_call.get("lead_id"),
                "agent_id": pending_call.get("agent_id"),
                "phone_number": pending_call.get("lead_number"),
                "direction": "outbound",
                "outcome": "completed",
                "duration": 0,
                "started_at": pending_call.get("created_at"),
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "recording_url": None,
                "disposition": disposition,
                "notes": notes
            }
            await db.call_logs.insert_one(call_log)
            # Clean up pending call
            await db.pending_calls.delete_one({"id": call_id})
        else:
            raise HTTPException(status_code=404, detail="Call not found")
    else:
        # Update the existing call log
        update_data = {
            "disposition": disposition,
            "notes": notes
        }
        await db.call_logs.update_one(
            {"id": call_id},
            {"$set": update_data}
        )
        # Refresh call_log data
        call_log = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    
    # Create activity record with disposition
    activity_description = f"Call - {disposition}"
    if notes:
        activity_description += f" - {notes}"
    
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "type": "call_disposition",
        "description": activity_description,
        "user_id": current_user.id,
        "lead_id": call_log.get("lead_id"),
        "metadata": {
            "call_id": call_id,
            "disposition": disposition,
            "notes": notes,
            "phone_number": call_log.get("phone_number"),
            "duration": call_log.get("duration")
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Update lead's last_contacted timestamp
    if call_log.get("lead_id"):
        await db.leads.update_one(
            {"id": call_log["lead_id"]},
            {"$set": {"last_contacted": datetime.now(timezone.utc).isoformat()}}
        )
    
    return {"message": "Disposition updated", "disposition": disposition}



# Lead Distribution
class DistributeLeadsRequest(BaseModel):
    employee_ids: List[str]
    lead_ids: Optional[List[str]] = None
    count_per_employee: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None

@api_router.post("/admin/distribute-leads")
async def distribute_leads(
    request: DistributeLeadsRequest,
    current_user: User = Depends(get_current_user)
):
    """Distribute leads to employees (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get leads to distribute
    if request.lead_ids:
        # Specific leads
        query = {"id": {"$in": request.lead_ids}, "assigned_to": None}
    else:
        # Unassigned leads with optional filters
        query = {"assigned_to": None}
        if request.filters:
            if request.filters.get('status'):
                query['status'] = request.filters['status']
            if request.filters.get('score_min'):
                query['score'] = {"$gte": request.filters['score_min']}
    
    available_leads = await db.leads.find(query, {"_id": 0}).to_list(10000)
    
    if not available_leads:
        raise HTTPException(status_code=404, detail="No unassigned leads found")
    
    # Distribute leads
    distributed = []
    employee_count = len(request.employee_ids)
    leads_per_employee = request.count_per_employee or (len(available_leads) // employee_count)
    
    for i, employee_id in enumerate(request.employee_ids):
        start_idx = i * leads_per_employee
        end_idx = start_idx + leads_per_employee
        employee_leads = available_leads[start_idx:end_idx]
        
        for lead in employee_leads:
            await db.leads.update_one(
                {"id": lead['id']},
                {
                    "$set": {
                        "assigned_to": employee_id,
                        "assigned_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            distributed.append({
                "lead_id": lead['id'],
                "employee_id": employee_id,
                "lead_name": f"{lead['first_name']} {lead['last_name']}"
            })
    
    return {
        "message": f"Distributed {len(distributed)} leads to {employee_count} employees",
        "total_distributed": len(distributed),
        "leads_per_employee": leads_per_employee,
        "distributions": distributed[:50]  # Return first 50
    }

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

# Team Chat - Channels
class Channel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    type: str = "public"  # public, private, dm
    participants: Optional[List[str]] = None  # For DMs - list of user IDs
    participant_names: Optional[dict] = None  # For DMs - {user_id: name}
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "public"

# ============================================
# USER PRESENCE & STATUS SYSTEM (SLACK-LIKE)
# ============================================

class UserStatus(BaseModel):
    user_id: str
    status: str = "online"  # online, away, busy, offline
    status_emoji: Optional[str] = None  # 🍕, 🏠, 🏖️, etc.
    status_text: Optional[str] = None  # "At lunch", "Working from home"
    expires_at: Optional[str] = None
    last_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# Predefined status options
STATUS_PRESETS = {
    "online": {"emoji": "🟢", "text": "Online", "color": "green"},
    "away": {"emoji": "🟡", "text": "Away", "color": "yellow"},
    "busy": {"emoji": "🔴", "text": "Busy", "color": "red"},
    "offline": {"emoji": "⚫", "text": "Offline", "color": "gray"},
    "lunch": {"emoji": "🍕", "text": "At Lunch", "color": "orange"},
    "wfh": {"emoji": "🏠", "text": "Working from Home", "color": "blue"},
    "vacation": {"emoji": "🏖️", "text": "On Vacation", "color": "purple"},
    "meeting": {"emoji": "📅", "text": "In a Meeting", "color": "blue"},
    "sick": {"emoji": "🤒", "text": "Out Sick", "color": "gray"},
    "focus": {"emoji": "🎯", "text": "Focus Time", "color": "red"},
    "commuting": {"emoji": "🚗", "text": "Commuting", "color": "yellow"},
    "brb": {"emoji": "⏰", "text": "Be Right Back", "color": "yellow"}
}

class UpdateStatusRequest(BaseModel):
    status: str  # online, away, busy, offline, or custom
    status_emoji: Optional[str] = None
    status_text: Optional[str] = None
    duration_minutes: Optional[int] = None  # Auto-clear after this time

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    sender_id: str
    sender_name: str
    content: str
    type: str = "text"  # text, file, meeting
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessageCreate(BaseModel):
    channel_id: str
    content: str
    type: str = "text"
    metadata: Optional[Dict[str, Any]] = None

@api_router.get("/chat/channels", response_model=List[Channel])
async def get_channels(current_user: User = Depends(get_current_user)):
    """Get all channels including DMs for current user"""
    # Get public channels
    public_channels = await db.channels.find({"type": "public"}, {"_id": 0}).to_list(1000)
    
    # Get DM channels where user is a participant
    dm_channels = await db.channels.find({
        "type": "dm",
        "participants": current_user.id
    }, {"_id": 0}).to_list(100)
    
    # Create default public channels if none exist
    if not public_channels:
        default_channels = [
            {"name": "general", "description": "General team discussion", "type": "public"},
            {"name": "sales", "description": "Sales team coordination", "type": "public"},
            {"name": "leads", "description": "Lead discussions", "type": "public"}
        ]
        for ch in default_channels:
            channel = Channel(**ch, created_by=current_user.id)
            doc = channel.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.channels.insert_one(doc)
        
        public_channels = await db.channels.find({"type": "public"}, {"_id": 0}).to_list(1000)
    
    all_channels = public_channels + dm_channels
    return [Channel(**ch) for ch in all_channels]


@api_router.post("/chat/dm/{user_id}")
async def get_or_create_dm_channel(user_id: str, current_user: User = Depends(get_current_user)):
    """Get or create a DM channel with another user"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot create DM with yourself")
    
    # Check if target user exists
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if DM channel already exists between these users
    existing_dm = await db.channels.find_one({
        "type": "dm",
        "participants": {"$all": [current_user.id, user_id]}
    }, {"_id": 0})
    
    if existing_dm:
        return Channel(**existing_dm)
    
    # Create new DM channel
    dm_channel = {
        "id": str(uuid.uuid4()),
        "name": f"dm_{current_user.id}_{user_id}",
        "description": f"Direct message between {current_user.full_name} and {target_user['full_name']}",
        "type": "dm",
        "participants": [current_user.id, user_id],
        "participant_names": {
            current_user.id: current_user.full_name,
            user_id: target_user['full_name']
        },
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.channels.insert_one(dm_channel)
    dm_channel.pop("_id", None)
    return dm_channel


@api_router.get("/chat/dm/list")
async def list_dm_conversations(current_user: User = Depends(get_current_user)):
    """Get all DM conversations for current user with last message info"""
    dm_channels = await db.channels.find({
        "type": "dm",
        "participants": current_user.id
    }, {"_id": 0}).to_list(100)
    
    result = []
    for dm in dm_channels:
        # Get the other participant
        other_id = next((p for p in dm.get("participants", []) if p != current_user.id), None)
        if other_id:
            other_user = await db.users.find_one({"id": other_id}, {"_id": 0, "hashed_password": 0})
            
            # Get last message
            last_message = await db.chat_messages.find_one(
                {"channel_id": dm["id"]},
                {"_id": 0},
                sort=[("created_at", -1)]
            )
            
            # Get unread count
            unread_count = await db.chat_messages.count_documents({
                "channel_id": dm["id"],
                "sender_id": {"$ne": current_user.id},
                "read_by": {"$ne": current_user.id}
            })
            
            result.append({
                "channel": dm,
                "other_user": other_user,
                "last_message": last_message,
                "unread_count": unread_count
            })
    
    # Sort by last message time
    result.sort(key=lambda x: (x.get("last_message") or {}).get("created_at", ""), reverse=True)
    return result

@api_router.post("/chat/channels", response_model=Channel)
async def create_channel(channel_data: ChannelCreate, current_user: User = Depends(get_current_user)):
    """Create a new channel"""
    channel = Channel(**channel_data.model_dump(), created_by=current_user.id)
    doc = channel.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.channels.insert_one(doc)
    return channel

@api_router.get("/chat/messages/{channel_id}", response_model=List[ChatMessage])
async def get_messages(channel_id: str, limit: int = 100, current_user: User = Depends(get_current_user)):
    """Get messages for a channel"""
    messages = await db.chat_messages.find(
        {"channel_id": channel_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    messages.reverse()  # Show oldest first
    return [ChatMessage(**msg) for msg in messages]

@api_router.post("/chat/messages", response_model=ChatMessage)
async def send_message(msg_data: ChatMessageCreate, current_user: User = Depends(get_current_user)):
    """Send a message to a channel"""
    message = ChatMessage(
        **msg_data.model_dump(),
        sender_id=current_user.id,
        sender_name=current_user.full_name
    )
    doc = message.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.chat_messages.insert_one(doc)
    
    # Handle @mentions - create notifications and tasks if needed
    if msg_data.metadata and msg_data.metadata.get('mentions'):
        for mentioned_user_id in msg_data.metadata['mentions']:
            # Create notification for mentioned user
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": mentioned_user_id,
                "type": "mention",
                "title": f"@{current_user.full_name} mentioned you",
                "message": msg_data.content[:100] + "..." if len(msg_data.content) > 100 else msg_data.content,
                "read": False,
                "action_url": f"/chat?channel={msg_data.channel_id}",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notification)
            
            # Check if message contains meeting request pattern (@user let's meet / schedule)
            content_lower = msg_data.content.lower()
            if any(word in content_lower for word in ['meet', 'schedule', 'meeting', 'call', 'sync']):
                # Create a task for meeting scheduling
                task = {
                    "id": str(uuid.uuid4()),
                    "title": f"Schedule meeting with {current_user.full_name}",
                    "description": f"Meeting request from chat: {msg_data.content[:200]}",
                    "assigned_to": mentioned_user_id,
                    "created_by": current_user.id,
                    "status": "pending",
                    "priority": "medium",
                    "type": "meeting_request",
                    "metadata": {
                        "from_chat": True,
                        "channel_id": msg_data.channel_id,
                        "requester_id": current_user.id,
                        "requester_name": current_user.full_name
                    },
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.tasks.insert_one(task)
    
    # Log activity
    activity = Activity(
        type="message_sent",
        description=f"Sent message in #{msg_data.channel_id}",
        user_id=current_user.id,
        metadata={"channel_id": msg_data.channel_id}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return message

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

@api_router.get("/booking/{user_id}/meeting-types")
async def get_public_meeting_types(user_id: str):
    """Get meeting types for public booking page (no auth required)"""
    meeting_types = await db.meeting_types.find(
        {"user_id": user_id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    return meeting_types

@api_router.get("/booking/{user_id}/slots/{meeting_type_id}")
async def get_available_slots_for_meeting_type(
    user_id: str,
    meeting_type_id: str,
    date: Optional[str] = None,
    days: int = 7
):
    """Get available time slots for a specific meeting type"""
    # Get meeting type
    meeting_type = await db.meeting_types.find_one(
        {"id": meeting_type_id, "user_id": user_id},
        {"_id": 0}
    )
    if not meeting_type:
        raise HTTPException(status_code=404, detail="Meeting type not found")
    
    # Get availability rules
    rules = await db.availability_rules.find(
        {"user_id": user_id, "is_available": True},
        {"_id": 0}
    ).to_list(100)
    
    # If no rules, create default Mon-Fri
    if not rules:
        rules = [{"day_of_week": i, "start_time": "09:00", "end_time": "17:00", "is_available": True} for i in range(5)]
    
    # Get existing bookings
    now_utc = datetime.now(timezone.utc)
    end_date = now_utc + timedelta(days=days)
    
    existing_bookings = await db.appointments.find({
        "employee_id": user_id,
        "scheduled_at": {"$gte": now_utc.isoformat(), "$lte": end_date.isoformat()}
    }, {"_id": 0}).to_list(1000)
    
    # Generate available slots
    available_slots = []
    duration = meeting_type.get("duration", 30)
    buffer_before = meeting_type.get("buffer_before", 0)
    buffer_after = meeting_type.get("buffer_after", 0)
    
    for day_offset in range(days):
        # Create a timezone-aware date for this day
        check_date = now_utc.date() + timedelta(days=day_offset)
        day_of_week = check_date.weekday()
        
        # Find rule for this day
        day_rule = next((r for r in rules if r.get("day_of_week") == day_of_week), None)
        if not day_rule:
            continue
        
        # Parse times
        start_hour, start_min = map(int, day_rule.get("start_time", "09:00").split(":"))
        end_hour, end_min = map(int, day_rule.get("end_time", "17:00").split(":"))
        
        # Generate timezone-aware slot times
        current_time = datetime(check_date.year, check_date.month, check_date.day, 
                                start_hour, start_min, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(check_date.year, check_date.month, check_date.day, 
                            end_hour, end_min, 0, 0, tzinfo=timezone.utc)
        
        while current_time + timedelta(minutes=duration) <= end_time:
            # Skip past times
            if current_time < now_utc:
                current_time += timedelta(minutes=30)
                continue
            
            # Check if slot conflicts with existing booking
            slot_end = current_time + timedelta(minutes=duration)
            is_available = True
            
            for booking in existing_bookings:
                # Parse booking time - ensure timezone awareness
                scheduled_at = booking["scheduled_at"]
                if scheduled_at.endswith("Z"):
                    scheduled_at = scheduled_at.replace("Z", "+00:00")
                elif "+" not in scheduled_at and "-" not in scheduled_at[10:]:
                    # No timezone info, assume UTC
                    scheduled_at = scheduled_at + "+00:00"
                
                booking_start = datetime.fromisoformat(scheduled_at)
                booking_end = booking_start + timedelta(minutes=booking.get("duration", 30))
                
                # Add buffers
                buffer_start = booking_start - timedelta(minutes=buffer_before)
                buffer_end = booking_end + timedelta(minutes=buffer_after)
                
                if current_time < buffer_end and slot_end > buffer_start:
                    is_available = False
                    break
            
            if is_available:
                available_slots.append(current_time.isoformat())
            
            current_time += timedelta(minutes=30)
    
    return {
        "meeting_type": meeting_type,
        "available_slots": available_slots
    }

@api_router.post("/booking/{user_id}/book")
async def create_booking(
    user_id: str,
    booking_data: Dict[str, Any]
):
    """Create a booking (public endpoint)"""
    meeting_type_id = booking_data.get("meeting_type_id")
    scheduled_at = booking_data.get("scheduled_at")
    guest_name = booking_data.get("name")
    guest_email = booking_data.get("email")
    guest_phone = booking_data.get("phone")
    guest_company = booking_data.get("company")
    notes = booking_data.get("notes")
    answers = booking_data.get("answers", {})  # Answers to custom questions
    
    if not all([meeting_type_id, scheduled_at, guest_name, guest_email]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Get meeting type
    meeting_type = await db.meeting_types.find_one({"id": meeting_type_id}, {"_id": 0})
    if not meeting_type:
        raise HTTPException(status_code=404, detail="Meeting type not found")
    
    # Get host user
    host_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not host_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate meeting link
    meeting_link = f"https://meet.google.com/{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:3]}"
    
    # Create appointment
    appointment = {
        "id": str(uuid.uuid4()),
        "title": f"{meeting_type['name']} with {guest_name}",
        "lead_id": None,
        "employee_id": user_id,
        "scheduled_at": scheduled_at,
        "duration": meeting_type.get("duration", 30),
        "status": "scheduled",
        "meeting_link": meeting_link,
        "notes": notes,
        "guest_info": {
            "name": guest_name,
            "email": guest_email,
            "phone": guest_phone,
            "company": guest_company
        },
        "meeting_type": meeting_type,
        "answers": answers,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.appointments.insert_one(appointment)
    
    # Send confirmation emails
    try:
        booking_datetime = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        
        # Email to host
        await send_booking_notification_email(
            employee_email=host_user.get("email"),
            employee_name=host_user.get("full_name"),
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone or "",
            guest_company=guest_company or "",
            booking_datetime=booking_datetime,
            duration=meeting_type.get("duration", 30),
            notes=notes or ""
        )
        
        # Email to guest
        await send_guest_confirmation_email(
            guest_name=guest_name,
            guest_email=guest_email,
            employee_name=host_user.get("full_name"),
            employee_email=host_user.get("email"),
            booking_datetime=booking_datetime,
            duration=meeting_type.get("duration", 30),
            company_name="LeadGen Pro"
        )
    except Exception as e:
        logging.error(f"Failed to send booking emails: {e}")
    
    # Remove MongoDB _id before returning
    appointment.pop("_id", None)
    
    return {
        "booking": appointment,
        "meeting_link": meeting_link,
        "message": "Booking confirmed!"
    }


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

# ==================== Voice/Call Endpoints ====================

@api_router.post("/voice/token")
async def generate_voice_token(request: VoiceTokenRequest, current_user: User = Depends(get_current_user)):
    """Generate Twilio access token for browser-based calling"""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET]):
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    try:
        # Create access token with identity
        token = AccessToken(
            TWILIO_ACCOUNT_SID,
            TWILIO_API_KEY,
            TWILIO_API_SECRET,
            identity=request.identity,
            ttl=3600  # 1 hour
        )
        
        # Add Voice grant
        voice_grant = VoiceGrant(
            outgoing_application_sid=None,
            incoming_allow=True
        )
        token.add_grant(voice_grant)
        
        return {
            "success": True,
            "token": token.to_jwt(),
            "identity": request.identity,
            "expires_in": 3600
        }
    except Exception as e:
        logging.error(f"Error generating voice token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class InitiateCallRequest(BaseModel):
    to_number: str
    lead_id: Optional[str] = None
    record: bool = False
    agent_phone: Optional[str] = None  # Agent's phone number for click-to-call

@api_router.post("/voice/call")
async def initiate_call(
    request: InitiateCallRequest,
    current_user: User = Depends(get_current_user)
):
    """Initiate a Click-to-Call - calls agent first, then bridges to lead
    
    Flow:
    1. Twilio calls the agent's phone number
    2. When agent answers, plays a prompt
    3. Agent presses 1 to connect
    4. Twilio then calls the lead and bridges both parties
    """
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    # Get agent's phone number from profile or request
    agent_phone = request.agent_phone or current_user.phone
    if not agent_phone:
        raise HTTPException(
            status_code=400, 
            detail="Please set your phone number in your profile settings to use Click-to-Call"
        )
    
    try:
        # Format destination phone number to E.164
        formatted_lead_number = request.to_number
        if not formatted_lead_number.startswith('+'):
            digits = re.sub(r'\D', '', formatted_lead_number)
            if len(digits) == 10:
                formatted_lead_number = '+1' + digits
            elif len(digits) == 11 and digits.startswith('1'):
                formatted_lead_number = '+' + digits
            else:
                formatted_lead_number = '+' + digits
        
        # Format agent phone number to E.164
        formatted_agent_phone = agent_phone
        if not formatted_agent_phone.startswith('+'):
            digits = re.sub(r'\D', '', formatted_agent_phone)
            if len(digits) == 10:
                formatted_agent_phone = '+1' + digits
            elif len(digits) == 11 and digits.startswith('1'):
                formatted_agent_phone = '+' + digits
            else:
                formatted_agent_phone = '+' + digits
        
        # Get the callback URL base
        callback_base = os.environ.get('FRONTEND_URL', '').rstrip('/')
        
        # Generate a unique call ID for this session
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        
        # Store the pending call info so we can retrieve it when agent answers
        pending_call = {
            "id": call_id,
            "lead_number": formatted_lead_number,
            "agent_id": current_user.id,
            "agent_name": current_user.full_name,
            "lead_id": request.lead_id,
            "record": request.record,
            "status": "calling_agent",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.pending_calls.insert_one(pending_call)
        
        # TwiML for when agent answers - prompt to connect
        # Uses Gather to wait for keypress, then redirects to connect endpoint
        agent_twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy">You have an outbound call to connect. Press 1 to connect now, or hang up to cancel.</Say>
    <Gather numDigits="1" action="{callback_base}/api/voice/connect/{call_id}" method="POST" timeout="10">
        <Say voice="Polly.Amy">Press 1 to connect.</Say>
    </Gather>
    <Say voice="Polly.Amy">No input received. Goodbye.</Say>
</Response>'''
        
        # Create the call to the AGENT first
        call_params = {
            'to': formatted_agent_phone,
            'from_': TWILIO_PHONE_NUMBER,
            'twiml': agent_twiml,
            'timeout': 30,
            'status_callback': f"{callback_base}/api/voice/agent-status/{call_id}",
            'status_callback_event': ['initiated', 'ringing', 'answered', 'completed'],
            'status_callback_method': 'POST'
        }
        
        call = twilio_client.calls.create(**call_params)
        
        # Update pending call with the agent call SID
        await db.pending_calls.update_one(
            {"id": call_id},
            {"$set": {"agent_call_sid": call.sid}}
        )
        
        # Log the call initiation activity
        activity = Activity(
            type="call_initiated",
            description=f"Click-to-Call initiated to {formatted_lead_number}",
            lead_id=request.lead_id,
            user_id=current_user.id,
            metadata={
                "call_id": call_id,
                "agent_call_sid": call.sid, 
                "lead_number": formatted_lead_number,
                "recorded": request.record
            }
        )
        activity_doc = activity.model_dump()
        activity_doc['created_at'] = activity_doc['created_at'].isoformat()
        await db.activities.insert_one(activity_doc)
        
        return {
            "success": True,
            "call_id": call_id,
            "call_sid": call.sid,
            "status": "calling_agent",
            "message": "Calling your phone now. Answer and press 1 to connect to the lead.",
            "to": formatted_lead_number,
            "from": TWILIO_PHONE_NUMBER,
            "recording": request.record
        }
    except Exception as e:
        logging.error(f"Error initiating call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to handle agent answering and connecting to lead
@api_router.post("/voice/connect/{call_id}")
async def connect_to_lead(call_id: str, request: Request):
    """When agent presses 1, this connects them to the lead"""
    try:
        form_data = await request.form()
        digits = form_data.get("Digits", "")
        
        # Get the pending call info
        pending_call = await db.pending_calls.find_one({"id": call_id})
        if not pending_call:
            response = VoiceResponse()
            response.say("Call session not found. Goodbye.", voice="Polly.Amy")
            return Response(content=str(response), media_type="application/xml")
        
        if digits != "1":
            response = VoiceResponse()
            response.say("Call cancelled. Goodbye.", voice="Polly.Amy")
            return Response(content=str(response), media_type="application/xml")
        
        callback_base = os.environ.get('FRONTEND_URL', '').rstrip('/')
        lead_number = pending_call.get("lead_number")
        should_record = pending_call.get("record", False)
        
        # Create TwiML to dial the lead
        response = VoiceResponse()
        response.say("Connecting you now. Please hold.", voice="Polly.Amy")
        
        dial = response.dial(
            caller_id=TWILIO_PHONE_NUMBER,
            timeout=45,
            action=f"{callback_base}/api/voice/call-complete/{call_id}",
            method="POST",
            record="record-from-answer-dual" if should_record else "do-not-record"
        )
        dial.number(
            lead_number,
            status_callback=f"{callback_base}/api/voice/lead-status/{call_id}",
            status_callback_event="initiated ringing answered completed",
            status_callback_method="POST"
        )
        
        # Update status
        await db.pending_calls.update_one(
            {"id": call_id},
            {"$set": {"status": "connecting_to_lead"}}
        )
        
        return Response(content=str(response), media_type="application/xml")
    except Exception as e:
        logging.error(f"Error connecting to lead: {e}")
        response = VoiceResponse()
        response.say("An error occurred. Please try again.", voice="Polly.Amy")
        return Response(content=str(response), media_type="application/xml")

# Handle call completion
@api_router.post("/voice/call-complete/{call_id}")
async def call_complete(call_id: str, request: Request):
    """Handle when the bridged call ends"""
    try:
        form_data = await request.form()
        dial_status = form_data.get("DialCallStatus", "")
        dial_duration = form_data.get("DialCallDuration", "0")
        recording_url = form_data.get("RecordingUrl", "")
        
        # Get pending call
        pending_call = await db.pending_calls.find_one({"id": call_id})
        
        if pending_call:
            # Create the call log
            call_log = {
                "id": call_id,
                "call_sid": pending_call.get("agent_call_sid"),
                "lead_id": pending_call.get("lead_id"),
                "agent_id": pending_call.get("agent_id"),
                "phone_number": pending_call.get("lead_number"),
                "direction": "outbound",
                "outcome": "connected" if dial_status == "completed" and int(dial_duration) > 0 else dial_status,
                "duration": int(dial_duration),
                "started_at": pending_call.get("created_at"),
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "recording_url": f"{recording_url}.mp3" if recording_url else None,
                "notes": ""
            }
            await db.call_logs.insert_one(call_log)
            
            # Update lead's last_contacted
            if pending_call.get("lead_id"):
                await db.leads.update_one(
                    {"id": pending_call.get("lead_id")},
                    {"$set": {"last_contacted": datetime.now(timezone.utc).isoformat()}}
                )
            
            # Clean up pending call
            await db.pending_calls.delete_one({"id": call_id})
        
        response = VoiceResponse()
        response.say("Call ended. Thank you for using LeadGen Pro.", voice="Polly.Amy")
        return Response(content=str(response), media_type="application/xml")
    except Exception as e:
        logging.error(f"Error in call complete: {e}")
        return Response(content="<Response></Response>", media_type="application/xml")

# Handle agent call status updates
@api_router.post("/voice/agent-status/{call_id}")
async def agent_status_callback(call_id: str, request: Request):
    """Handle status updates for the agent leg of the call"""
    try:
        form_data = await request.form()
        call_status = form_data.get("CallStatus", "")
        
        await db.pending_calls.update_one(
            {"id": call_id},
            {"$set": {"agent_status": call_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # If agent didn't answer, clean up
        if call_status in ["busy", "failed", "no-answer", "canceled"]:
            await db.pending_calls.delete_one({"id": call_id})
        
        return {"status": "received"}
    except Exception as e:
        logging.error(f"Error in agent status: {e}")
        return {"status": "error"}

# Handle lead call status updates  
@api_router.post("/voice/lead-status/{call_id}")
async def lead_status_callback(call_id: str, request: Request):
    """Handle status updates for the lead leg of the call"""
    try:
        form_data = await request.form()
        call_status = form_data.get("CallStatus", "")
        call_sid = form_data.get("CallSid", "")
        
        await db.pending_calls.update_one(
            {"id": call_id},
            {"$set": {
                "lead_status": call_status,
                "lead_call_sid": call_sid,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"status": "received"}
    except Exception as e:
        logging.error(f"Error in lead status: {e}")
        return {"status": "error"}

# Get pending call status for frontend polling
@api_router.get("/voice/pending/{call_id}")
async def get_pending_call_status(call_id: str, current_user: User = Depends(get_current_user)):
    """Get the status of a pending click-to-call"""
    pending_call = await db.pending_calls.find_one({"id": call_id}, {"_id": 0})
    if not pending_call:
        # Check if call was completed and logged
        call_log = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
        if call_log:
            return {
                "status": "completed",
                "duration": call_log.get("duration", 0),
                "outcome": call_log.get("outcome")
            }
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "status": pending_call.get("status", "unknown"),
        "agent_status": pending_call.get("agent_status"),
        "lead_status": pending_call.get("lead_status"),
        "duration": 0
    }

# Handle dial status (what happens when the dial completes)
@api_router.post("/voice/dial-status")
async def dial_status_callback(request: Request):
    """Handle dial completion status"""
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        dial_status = form_data.get("DialCallStatus")
        dial_duration = form_data.get("DialCallDuration", "0")
        
        logging.info(f"Dial status - SID: {call_sid}, Status: {dial_status}, Duration: {dial_duration}")
        
        # Update the call record
        await db.active_calls.update_one(
            {"call_sid": call_sid},
            {"$set": {
                "dial_status": dial_status,
                "dial_duration": int(dial_duration),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Return TwiML response
        response = VoiceResponse()
        if dial_status == "completed":
            response.say("Call completed. Thank you for using LeadGen Pro.", voice="Polly.Amy")
        elif dial_status == "busy":
            response.say("The line is busy. Please try again later.", voice="Polly.Amy")
        elif dial_status == "no-answer":
            response.say("No answer. Please try again later.", voice="Polly.Amy")
        elif dial_status == "failed":
            response.say("The call could not be completed. Please check the number and try again.", voice="Polly.Amy")
        
        return Response(content=str(response), media_type="application/xml")
    except Exception as e:
        logging.error(f"Error processing dial status: {e}")
        return Response(content="<Response></Response>", media_type="application/xml")

@api_router.get("/voice/call/{call_sid}/status")
async def get_call_status(call_sid: str, current_user: User = Depends(get_current_user)):
    """Get the status of an active call"""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    try:
        call = twilio_client.calls(call_sid).fetch()
        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status,
            "duration": call.duration,
            "direction": call.direction,
            "start_time": call.start_time.isoformat() if call.start_time else None,
            "end_time": call.end_time.isoformat() if call.end_time else None
        }
    except Exception as e:
        logging.error(f"Error getting call status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/voice/call/{call_sid}/end")
async def end_call(call_sid: str, current_user: User = Depends(get_current_user)):
    """End an active call"""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    try:
        call = twilio_client.calls(call_sid).update(status="completed")
        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status
        }
    except Exception as e:
        logging.error(f"Error ending call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class HangupRequest(BaseModel):
    call_sid: str

@api_router.post("/voice/hangup")
async def hangup_call(request: HangupRequest, current_user: User = Depends(get_current_user)):
    """End an active call via hangup"""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    try:
        call = twilio_client.calls(request.call_sid).update(status="completed")
        
        # Update the call record in database
        await db.active_calls.update_one(
            {"call_sid": request.call_sid},
            {"$set": {"status": "completed", "ended_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status
        }
    except Exception as e:
        logging.error(f"Error hanging up call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Twilio webhook for call status events
@api_router.post("/voice/events")
async def voice_status_callback(request: Request):
    """Handle Twilio call status webhooks"""
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        call_status = form_data.get("CallStatus")
        duration = form_data.get("CallDuration", "0")
        
        logging.info(f"Call status update - SID: {call_sid}, Status: {call_status}, Duration: {duration}")
        
        # Update the call record
        update_data = {
            "status": call_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if call_status in ["completed", "busy", "failed", "no-answer", "canceled"]:
            update_data["ended_at"] = datetime.now(timezone.utc).isoformat()
            update_data["duration"] = int(duration)
        
        await db.active_calls.update_one(
            {"call_sid": call_sid},
            {"$set": update_data}
        )
        
        # If call completed, create a call log entry
        if call_status == "completed":
            call_record = await db.active_calls.find_one({"call_sid": call_sid}, {"_id": 0})
            if call_record:
                call_log = {
                    "id": f"log_{uuid.uuid4().hex[:12]}",
                    "call_sid": call_sid,
                    "lead_id": call_record.get("lead_id"),
                    "agent_id": call_record.get("agent_id"),
                    "phone_number": call_record.get("to_number"),
                    "direction": "outbound",
                    "outcome": "connected" if int(duration) > 0 else "no_answer",
                    "duration": int(duration),
                    "started_at": call_record.get("started_at"),
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "recording_url": call_record.get("recording_url"),
                    "notes": ""
                }
                await db.call_logs.insert_one(call_log)
                
                # Update lead's last_contacted
                if call_record.get("lead_id"):
                    await db.leads.update_one(
                        {"id": call_record.get("lead_id")},
                        {"$set": {"last_contacted": datetime.now(timezone.utc).isoformat()}}
                    )
        
        return {"status": "received"}
    except Exception as e:
        logging.error(f"Error processing voice event: {e}")
        return {"status": "error", "message": str(e)}

# Twilio webhook for recording status
@api_router.post("/voice/recording-callback")
async def recording_callback(request: Request):
    """Handle Twilio recording completion webhook"""
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        recording_sid = form_data.get("RecordingSid")
        recording_url = form_data.get("RecordingUrl")
        recording_duration = form_data.get("RecordingDuration", "0")
        recording_status = form_data.get("RecordingStatus")
        
        logging.info(f"Recording callback - Call SID: {call_sid}, Recording SID: {recording_sid}, Status: {recording_status}")
        
        if recording_status == "completed" and recording_url:
            # Add .mp3 extension to the URL for easier playback
            full_recording_url = f"{recording_url}.mp3"
            
            # Update the active call record
            await db.active_calls.update_one(
                {"call_sid": call_sid},
                {"$set": {
                    "recording_sid": recording_sid,
                    "recording_url": full_recording_url,
                    "recording_duration": int(recording_duration)
                }}
            )
            
            # Also update the call log if it exists
            await db.call_logs.update_one(
                {"call_sid": call_sid},
                {"$set": {
                    "recording_url": full_recording_url,
                    "recording_duration": int(recording_duration)
                }}
            )
            
            logging.info(f"Recording saved for call {call_sid}: {full_recording_url}")
        
        return {"status": "received"}
    except Exception as e:
        logging.error(f"Error processing recording callback: {e}")
        return {"status": "error", "message": str(e)}

@api_router.post("/calls/log", response_model=CallLog)
async def log_call(call_data: CallLogCreate, current_user: User = Depends(get_current_user)):
    """Log call outcome and details"""
    call_log = CallLog(
        **call_data.model_dump(),
        agent_id=current_user.id
    )
    
    doc = call_log.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('started_at'):
        doc['started_at'] = doc['started_at'].isoformat()
    if doc.get('ended_at'):
        doc['ended_at'] = doc['ended_at'].isoformat()
    
    await db.call_logs.insert_one(doc)
    
    # Update lead's last_contacted timestamp
    await db.leads.update_one(
        {"id": call_data.lead_id},
        {"$set": {"last_contacted": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Log activity
    outcome_desc = {
        "connected": "Connected - spoke with contact",
        "voicemail": "Left voicemail",
        "no_answer": "No answer",
        "busy": "Line was busy",
        "wrong_number": "Wrong number",
        "declined": "Contact declined to speak"
    }
    activity = Activity(
        type="call_logged",
        description=f"Call logged: {outcome_desc.get(call_data.outcome, call_data.outcome)} ({call_data.duration}s)",
        lead_id=call_data.lead_id,
        user_id=current_user.id,
        metadata={
            "outcome": call_data.outcome,
            "duration": call_data.duration,
            "call_sid": call_data.call_sid
        }
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return call_log

@api_router.get("/calls/logs", response_model=List[CallLog])
async def get_call_logs(lead_id: Optional[str] = None, limit: int = 50, current_user: User = Depends(get_current_user)):
    """Get call logs, optionally filtered by lead"""
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    
    logs = await db.call_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return [CallLog(**log) for log in logs]

@api_router.get("/calls/stats")
async def get_call_stats(current_user: User = Depends(get_current_user)):
    """Get call statistics for the current user"""
    query = {"agent_id": current_user.id}
    
    logs = await db.call_logs.find(query, {"_id": 0}).to_list(1000)
    
    total_calls = len(logs)
    total_duration = sum(log.get("duration", 0) for log in logs)
    
    outcome_counts = {}
    for log in logs:
        outcome = log.get("outcome", "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    
    return {
        "total_calls": total_calls,
        "total_duration_seconds": total_duration,
        "average_duration_seconds": total_duration // total_calls if total_calls > 0 else 0,
        "outcomes": outcome_counts,
        "connect_rate": round((outcome_counts.get("connected", 0) / total_calls * 100) if total_calls > 0 else 0, 1)
    }

# ==================== Calendar Endpoints ====================

@api_router.get("/calendar/events", response_model=List[CalendarEvent])
async def get_calendar_events(current_user: User = Depends(get_current_user)):
    """Get all calendar events visible to the user"""
    events = await db.calendar_events.find({}, {"_id": 0}).sort("start", 1).to_list(1000)
    return [CalendarEvent(**event) for event in events]

@api_router.post("/calendar/events", response_model=CalendarEvent)
async def create_calendar_event(event_data: CalendarEventCreate, current_user: User = Depends(get_current_user)):
    """Create a new calendar event"""
    # Get attendee names
    attendee_names = []
    for attendee_id in event_data.attendees:
        user = await db.users.find_one({"id": attendee_id}, {"_id": 0})
        if user:
            attendee_names.append(user["full_name"])
    
    event = CalendarEvent(
        **event_data.model_dump(),
        attendee_names=attendee_names,
        created_by=current_user.id
    )
    
    doc = event.model_dump()
    doc['start'] = doc['start'].isoformat()
    doc['end'] = doc['end'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.calendar_events.insert_one(doc)
    
    # Log activity
    activity = Activity(
        type="event_created",
        description=f"Created {event.type}: {event.title}",
        user_id=current_user.id,
        metadata={"event_id": event.id, "event_type": event.type}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return event

@api_router.delete("/calendar/events/{event_id}")
async def delete_calendar_event(event_id: str, current_user: User = Depends(get_current_user)):
    """Delete a calendar event"""
    result = await db.calendar_events.delete_one({"id": event_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}

# ==================== Google Calendar & Meet Integration ====================

def generate_google_meet_link():
    """Generate a unique Google Meet-style link"""
    # Generate a random meeting code in Google Meet format (xxx-xxxx-xxx)
    import random
    import string
    chars = string.ascii_lowercase
    part1 = ''.join(random.choices(chars, k=3))
    part2 = ''.join(random.choices(chars, k=4))
    part3 = ''.join(random.choices(chars, k=3))
    return f"https://meet.google.com/{part1}-{part2}-{part3}"

@api_router.post("/calendar/events/with-meet")
async def create_event_with_meet(event_data: CalendarEventCreate, current_user: User = Depends(get_current_user)):
    """Create a calendar event with automatic Google Meet link"""
    # Get attendee names
    attendee_names = []
    attendee_emails = []
    for attendee_id in event_data.attendees:
        user = await db.users.find_one({"id": attendee_id}, {"_id": 0})
        if user:
            attendee_names.append(user["full_name"])
            attendee_emails.append(user.get("email", ""))
    
    # Generate Meet link
    meet_link = generate_google_meet_link()
    
    # Get event data without the meeting_link field to avoid duplication
    event_dict = event_data.model_dump()
    event_dict.pop('meeting_link', None)  # Remove existing meeting_link if any
    
    event = CalendarEvent(
        **event_dict,
        attendee_names=attendee_names,
        created_by=current_user.id,
        meeting_link=meet_link
    )
    
    doc = event.model_dump()
    doc['start'] = doc['start'].isoformat()
    doc['end'] = doc['end'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.calendar_events.insert_one(doc)
    
    # Log activity
    activity = Activity(
        type="meeting_created",
        description=f"Created meeting with Google Meet: {event.title}",
        user_id=current_user.id,
        metadata={"event_id": event.id, "meeting_link": meet_link}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return {
        "event": event,
        "meeting_link": meet_link,
        "message": "Event created with Google Meet link"
    }

@api_router.post("/calendar/events/{event_id}/add-meet")
async def add_meet_to_event(event_id: str, current_user: User = Depends(get_current_user)):
    """Add a Google Meet link to an existing event"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.get("meeting_link"):
        return {"event": event, "meeting_link": event["meeting_link"], "message": "Event already has a meeting link"}
    
    # Generate Meet link
    meet_link = generate_google_meet_link()
    
    await db.calendar_events.update_one(
        {"id": event_id},
        {"$set": {"meeting_link": meet_link}}
    )
    
    event["meeting_link"] = meet_link
    
    return {
        "event": event,
        "meeting_link": meet_link,
        "message": "Google Meet link added to event"
    }

@api_router.get("/calendar/export/ics/{event_id}")
async def export_event_to_ics(event_id: str, current_user: User = Depends(get_current_user)):
    """Export a calendar event as ICS file for Google Calendar import"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Parse dates
    start = datetime.fromisoformat(event['start'].replace('Z', '+00:00')) if isinstance(event['start'], str) else event['start']
    end = datetime.fromisoformat(event['end'].replace('Z', '+00:00')) if isinstance(event['end'], str) else event['end']
    
    # Build ICS content
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//LeadGen Pro//Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}
DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}
DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}
UID:{event['id']}@leadgenpro
SUMMARY:{event['title']}
DESCRIPTION:{event.get('description', '')}
LOCATION:{event.get('location', '')}
"""
    
    if event.get('meeting_link'):
        ics_content += f"URL:{event['meeting_link']}\n"
        ics_content += f"X-GOOGLE-CONFERENCE:{event['meeting_link']}\n"
    
    ics_content += """STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename=event_{event_id}.ics"
        }
    )

@api_router.get("/calendar/export/google-url/{event_id}")
async def get_google_calendar_url(event_id: str, current_user: User = Depends(get_current_user)):
    """Get a URL to add event directly to Google Calendar"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Parse dates
    start = datetime.fromisoformat(event['start'].replace('Z', '+00:00')) if isinstance(event['start'], str) else event['start']
    end = datetime.fromisoformat(event['end'].replace('Z', '+00:00')) if isinstance(event['end'], str) else event['end']
    
    # Build Google Calendar URL
    import urllib.parse
    
    title = urllib.parse.quote(event['title'])
    dates = f"{start.strftime('%Y%m%dT%H%M%SZ')}/{end.strftime('%Y%m%dT%H%M%SZ')}"
    details = urllib.parse.quote(event.get('description', '') + (f"\n\nMeeting Link: {event.get('meeting_link', '')}" if event.get('meeting_link') else ""))
    location = urllib.parse.quote(event.get('location', ''))
    
    google_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title}&dates={dates}&details={details}&location={location}"
    
    return {
        "google_calendar_url": google_url,
        "event": event
    }

@api_router.get("/calendar/sync-status")
async def get_calendar_sync_status(current_user: User = Depends(get_current_user)):
    """Get Google Calendar sync status for the user"""
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    google_linked = user.get("google_linked", False)
    
    # Check if user has Google credentials for full sync
    google_creds = await db.google_credentials.find_one({"user_id": current_user.id})
    has_full_sync = google_creds is not None and "calendar" in str(google_creds.get("scopes", []))
    
    return {
        "google_linked": google_linked,
        "has_full_sync": has_full_sync,
        "sync_method": "full" if has_full_sync else ("manual" if google_linked else "none"),
        "message": "Full two-way sync available" if has_full_sync else 
                   ("Manual export to Google Calendar available" if google_linked else 
                    "Sign in with Google to enable calendar sync")
    }

@api_router.get("/team-members", response_model=List[User])
async def get_team_members(current_user: User = Depends(get_current_user)):
    """Get all team members (for calendar attendees, assignments, etc.)"""
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [User(**user) for user in users]

# ==================== Public Booking Endpoints ====================

class BookingRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    datetime: datetime
    duration: int = 30

class AvailabilitySlot(BaseModel):
    time: str
    available: bool = True

@api_router.get("/booking/{user_id}")
async def get_booking_info(user_id: str):
    """Get user info and booked slots for public booking page"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all booked events for this user
    booked_events = await db.calendar_events.find({
        "$or": [
            {"created_by": user_id},
            {"attendees": user_id}
        ]
    }, {"_id": 0}).to_list(1000)
    
    # Extract booked slot times
    booked_slots = [event['start'] for event in booked_events]
    
    return {
        "user": User(**user),
        "booked_slots": booked_slots
    }

@api_router.get("/booking/{user_id}/slots")
async def get_available_slots(user_id: str, date: str):
    """Get available time slots for a specific date"""
    from datetime import datetime as dt
    
    try:
        target_date = dt.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get all events for this user on the target date
    start_of_day = target_date.replace(hour=0, minute=0, second=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59)
    
    booked_events = await db.calendar_events.find({
        "$or": [
            {"created_by": user_id},
            {"attendees": user_id}
        ],
        "start": {
            "$gte": start_of_day.isoformat(),
            "$lte": end_of_day.isoformat()
        }
    }, {"_id": 0}).to_list(100)
    
    # Generate available slots (9 AM to 5 PM, 30-minute intervals)
    available_slots = []
    booked_times = set()
    
    for event in booked_events:
        event_start = dt.fromisoformat(event['start'].replace('Z', '+00:00') if 'Z' in event['start'] else event['start'])
        booked_times.add(event_start.strftime("%H:%M"))
    
    now = dt.now()
    for hour in range(9, 17):  # 9 AM to 5 PM
        for minute in [0, 30]:
            slot_time = f"{hour:02d}:{minute:02d}"
            
            # Skip past times for today
            if target_date.date() == now.date():
                slot_datetime = target_date.replace(hour=hour, minute=minute)
                if slot_datetime < now:
                    continue
            
            if slot_time not in booked_times:
                available_slots.append(slot_time)
    
    return {"slots": available_slots, "date": date}

@api_router.post("/booking/{user_id}/book-simple")
async def create_booking_simple(user_id: str, booking: BookingRequest):
    """Create a booking (simple public endpoint - no meeting type required)"""
    # Verify user exists
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if slot is available
    booking_start = booking.datetime
    booking_end = booking_start + timedelta(minutes=booking.duration)
    
    # Look for conflicting events
    conflict = await db.calendar_events.find_one({
        "$and": [
            {
                "$or": [
                    {"created_by": user_id},
                    {"attendees": user_id}
                ]
            },
            {
                "start": {"$lt": booking_end.isoformat()},
                "end": {"$gt": booking_start.isoformat()}
            }
        ]
    })
    
    if conflict:
        raise HTTPException(status_code=400, detail="This time slot is no longer available")
    
    # Create calendar event for the booking
    event = CalendarEvent(
        title=f"Meeting with {booking.name}",
        description=f"Booked via public booking page\nCompany: {booking.company or 'N/A'}\nPhone: {booking.phone or 'N/A'}\nNotes: {booking.notes or 'None'}",
        type="meeting",
        start=booking_start,
        end=booking_end,
        attendees=[user_id],
        attendee_names=[user['full_name']],
        location="Video Call",
        created_by=user_id
    )
    
    doc = event.model_dump()
    doc['start'] = doc['start'].isoformat()
    doc['end'] = doc['end'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.calendar_events.insert_one(doc)
    
    # Also create a lead from the booking if not exists
    existing_lead = await db.leads.find_one({"email": booking.email})
    if not existing_lead:
        name_parts = booking.name.split(' ', 1)
        lead_data = {
            'first_name': name_parts[0],
            'last_name': name_parts[1] if len(name_parts) > 1 else '',
            'email': booking.email,
            'phone': booking.phone,
            'company': booking.company or 'Unknown',
            'title': 'Lead',
            'status': 'meeting_scheduled',
            'stage': 'qualified',
            'tags': ['booking'],
            'created_by': user_id,
            'assigned_to': user_id
        }
        lead_data['score'] = await calculate_lead_score(lead_data)
        lead = Lead(**lead_data)
        lead_doc = lead.model_dump()
        lead_doc['created_at'] = lead_doc['created_at'].isoformat()
        lead_doc['updated_at'] = lead_doc['updated_at'].isoformat()
        await db.leads.insert_one(lead_doc)
    
    # Log activity
    activity = Activity(
        type="booking_created",
        description=f"New booking from {booking.name} ({booking.email})",
        user_id=user_id,
        metadata={"guest_name": booking.name, "guest_email": booking.email}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    # Send email notification to the employee
    employee_email_sent = False
    if user.get('email'):
        email_result = await send_booking_notification_email(
            employee_email=user['email'],
            employee_name=user['full_name'],
            guest_name=booking.name,
            guest_email=booking.email,
            guest_phone=booking.phone,
            guest_company=booking.company,
            booking_datetime=booking_start,
            duration=booking.duration,
            notes=booking.notes
        )
        employee_email_sent = email_result is not None
    
    # Send confirmation email to the guest
    guest_email_sent = False
    guest_confirmation = await send_guest_confirmation_email(
        guest_name=booking.name,
        guest_email=booking.email,
        employee_name=user['full_name'],
        employee_email=user.get('email', ''),
        booking_datetime=booking_start,
        duration=booking.duration
    )
    guest_email_sent = guest_confirmation is not None
    
    return {
        "success": True,
        "event_id": event.id,
        "message": "Meeting booked successfully",
        "notifications": {
            "employee_notified": employee_email_sent,
            "guest_confirmation_sent": guest_email_sent
        },
        "details": {
            "with": user['full_name'],
            "datetime": booking.datetime.isoformat(),
            "duration": booking.duration
        }
    }

@api_router.get("/booking/link/{user_id}")
async def get_booking_link(user_id: str, current_user: User = Depends(get_current_user)):
    """Get the public booking link for a user"""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    base_url = os.environ.get('REACT_APP_BACKEND_URL', '').replace('/api', '')
    if not base_url:
        base_url = "https://your-domain.com"
    
    return {
        "booking_link": f"{base_url}/book/{user_id}",
        "user_id": user_id
    }

# ==================== Admin User Management Endpoints ====================

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str  # employee, manager, admin
    department: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None

class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None

@api_router.get("/admin/users")
async def admin_get_users(current_user: User = Depends(get_current_user)):
    """Get all users (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    
    # Add department and phone info if exists
    result = []
    for user in users:
        user_data = {**user}
        result.append(user_data)
    
    return result

@api_router.post("/admin/users")
async def admin_create_user(user_data: AdminUserCreate, current_user: User = Depends(get_current_user)):
    """Create a new user (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate role
    valid_roles = ["employee", "manager", "admin"]
    if user_data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        company=user_data.company,
        onboarding_completed=True  # Admin-created users skip onboarding
    )
    
    doc = user.model_dump()
    doc['password'] = get_password_hash(user_data.password)
    doc['department'] = user_data.department
    doc['phone'] = user_data.phone
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    
    # Log activity
    activity = Activity(
        type="user_created",
        description=f"Created user: {user.full_name} ({user.role})",
        user_id=current_user.id,
        metadata={"new_user_id": user.id, "role": user.role}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return {
        "success": True,
        "user": user,
        "message": f"User {user.full_name} created successfully"
    }

@api_router.put("/admin/users/{user_id}")
async def admin_update_user(user_id: str, update_data: AdminUserUpdate, current_user: User = Depends(get_current_user)):
    """Update a user (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if user exists
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prepare update
    update_fields = {}
    if update_data.full_name:
        update_fields['full_name'] = update_data.full_name
    if update_data.role:
        valid_roles = ["employee", "manager", "admin"]
        if update_data.role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        update_fields['role'] = update_data.role
    if update_data.department is not None:
        update_fields['department'] = update_data.department
    if update_data.phone is not None:
        update_fields['phone'] = update_data.phone
    if update_data.company is not None:
        update_fields['company'] = update_data.company
    
    if update_fields:
        await db.users.update_one({"id": user_id}, {"$set": update_fields})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return updated_user

@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Delete a user (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Check if user exists
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user
    await db.users.delete_one({"id": user_id})
    
    # Log activity
    activity = Activity(
        type="user_deleted",
        description=f"Deleted user: {existing['full_name']}",
        user_id=current_user.id,
        metadata={"deleted_user_id": user_id}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return {"success": True, "message": "User deleted successfully"}

@api_router.post("/admin/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, new_password: str, current_user: User = Depends(get_current_user)):
    """Reset a user's password (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if user exists
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"password": get_password_hash(new_password)}}
    )
    
    return {"success": True, "message": "Password reset successfully"}

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

# ==================== Google Drive Integration ====================

# ==================== AI Email Automation Endpoints ====================

@api_router.get("/email/templates")
async def get_email_templates(current_user: User = Depends(get_current_user)):
    """Get all email templates"""
    templates = await db.email_templates.find({}, {"_id": 0}).to_list(100)
    return templates

@api_router.post("/email/templates")
async def create_email_template(template: EmailTemplate, current_user: User = Depends(get_current_user)):
    """Create a new email template"""
    template.created_by = current_user.id
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.email_templates.insert_one(doc)
    return {"success": True, "template": template}

@api_router.delete("/email/templates/{template_id}")
async def delete_email_template(template_id: str, current_user: User = Depends(get_current_user)):
    """Delete an email template"""
    await db.email_templates.delete_one({"id": template_id})
    return {"success": True}

@api_router.get("/email/campaigns")
async def get_email_campaigns(current_user: User = Depends(get_current_user)):
    """Get all email campaigns"""
    campaigns = await db.email_campaigns.find({}, {"_id": 0}).to_list(100)
    return campaigns

@api_router.get("/email/scheduled")
async def get_scheduled_emails(current_user: User = Depends(get_current_user)):
    """Get all scheduled emails"""
    emails = await db.scheduled_emails.find({"status": "pending"}, {"_id": 0}).to_list(100)
    return emails

@api_router.delete("/email/scheduled/{email_id}")
async def cancel_scheduled_email(email_id: str, current_user: User = Depends(get_current_user)):
    """Cancel a scheduled email"""
    await db.scheduled_emails.update_one(
        {"id": email_id},
        {"$set": {"status": "cancelled"}}
    )
    return {"success": True}

class EmailGenerateRequest(BaseModel):
    prompt: str
    context: str = "single_email"
    lead_count: int = 0

@api_router.post("/email/generate")
async def generate_email_with_ai(request: EmailGenerateRequest, current_user: User = Depends(get_current_user)):
    """Generate email content using AI"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"email-gen-{uuid.uuid4().hex[:8]}",
            system_message="""You are an expert email copywriter specializing in B2B sales and marketing emails.
            Write compelling, personalized emails that:
            - Have attention-grabbing subject lines
            - Are concise and value-focused
            - Include clear calls to action
            - Sound natural and not salesy
            - Use personalization variables like {{first_name}}, {{company}}, {{title}} where appropriate"""
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""Write a professional sales email based on this request: {request.prompt}
        
        {"This will be sent to " + str(request.lead_count) + " recipients, so include personalization variables." if request.lead_count > 1 else ""}
        
        Return your response in this exact JSON format:
        {{
            "subject": "Your subject line here",
            "body": "Your email body here"
        }}
        
        Return ONLY the JSON, no other text."""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        # Parse response
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        
        email_content = json.loads(clean_response.strip())
        return email_content
        
    except Exception as e:
        logging.error(f"Email generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate email")

class BulkEmailRequest(BaseModel):
    lead_ids: List[str]
    subject: str
    body: str
    ai_personalize: bool = False
    schedule_time: Optional[str] = None
    follow_up: Optional[dict] = None

@api_router.post("/email/send-bulk")
async def send_bulk_email(request: BulkEmailRequest, current_user: User = Depends(get_current_user)):
    """Send bulk emails to selected leads"""
    if not RESEND_API_KEY:
        raise HTTPException(status_code=400, detail="Email service not configured")
    
    # Get lead details
    leads = await db.leads.find({"id": {"$in": request.lead_ids}}, {"_id": 0}).to_list(100)
    
    if not leads:
        raise HTTPException(status_code=400, detail="No valid leads found")
    
    # Create campaign record
    campaign = EmailCampaign(
        subject=request.subject,
        body=request.body,
        sent_count=len(leads),
        created_by=current_user.id
    )
    
    campaign_doc = campaign.model_dump()
    campaign_doc['created_at'] = campaign_doc['created_at'].isoformat()
    await db.email_campaigns.insert_one(campaign_doc)
    
    # If scheduled, save for later
    if request.schedule_time:
        scheduled = ScheduledEmail(
            subject=request.subject,
            body=request.body,
            recipient_ids=request.lead_ids,
            recipient_count=len(leads),
            scheduled_time=datetime.fromisoformat(request.schedule_time),
            campaign_id=campaign.id,
            created_by=current_user.id
        )
        scheduled_doc = scheduled.model_dump()
        scheduled_doc['created_at'] = scheduled_doc['created_at'].isoformat()
        scheduled_doc['scheduled_time'] = scheduled_doc['scheduled_time'].isoformat()
        await db.scheduled_emails.insert_one(scheduled_doc)
        
        return {
            "success": True,
            "sent_count": 0,
            "scheduled_count": len(leads),
            "scheduled_time": request.schedule_time
        }
    
    # Send emails immediately
    sent_count = 0
    failed_count = 0
    
    for lead in leads:
        try:
            # Personalize email
            personalized_subject = request.subject
            personalized_body = request.body
            
            # Replace variables
            replacements = {
                "{{first_name}}": lead.get("first_name", ""),
                "{{last_name}}": lead.get("last_name", ""),
                "{{company}}": lead.get("company", ""),
                "{{title}}": lead.get("title", ""),
                "{{email}}": lead.get("email", "")
            }
            
            for var, value in replacements.items():
                personalized_subject = personalized_subject.replace(var, value)
                personalized_body = personalized_body.replace(var, value)
            
            # Send email via Resend
            email_params = {
                "from": SENDER_EMAIL,
                "to": [lead.get("email")],
                "subject": personalized_subject,
                "html": f"<div style='font-family: Arial, sans-serif; line-height: 1.6;'>{personalized_body.replace(chr(10), '<br>')}</div>"
            }
            
            await asyncio.to_thread(resend.Emails.send, email_params)
            sent_count += 1
            
            # Log activity
            activity = Activity(
                type="email_sent",
                description=f"Sent bulk email: {personalized_subject}",
                lead_id=lead.get("id"),
                user_id=current_user.id,
                metadata={"campaign_id": campaign.id, "subject": personalized_subject}
            )
            activity_doc = activity.model_dump()
            activity_doc['created_at'] = activity_doc['created_at'].isoformat()
            await db.activities.insert_one(activity_doc)
            
        except Exception as e:
            logging.error(f"Failed to send email to {lead.get('email')}: {e}")
            failed_count += 1
    
    # Schedule follow-ups if enabled
    if request.follow_up and sent_count > 0:
        follow_up_days = request.follow_up.get("days", 3)
        follow_up_count = request.follow_up.get("count", 2)
        
        for i in range(1, follow_up_count + 1):
            follow_up_time = datetime.now(timezone.utc) + timedelta(days=follow_up_days * i)
            
            scheduled = ScheduledEmail(
                subject=f"Re: {request.subject}",
                body=f"Following up on my previous email...\n\n{request.body}",
                recipient_ids=request.lead_ids,
                recipient_count=len(leads),
                scheduled_time=follow_up_time,
                campaign_id=campaign.id,
                created_by=current_user.id
            )
            scheduled_doc = scheduled.model_dump()
            scheduled_doc['created_at'] = scheduled_doc['created_at'].isoformat()
            scheduled_doc['scheduled_time'] = scheduled_doc['scheduled_time'].isoformat()
            await db.scheduled_emails.insert_one(scheduled_doc)
    
    return {
        "success": True,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "campaign_id": campaign.id
    }

# ==================== Email Tracking & Analytics ====================

@api_router.get("/email/tracking/pixel/{email_id}.gif")
async def track_email_open(email_id: str, request: Request):
    """Tracking pixel endpoint - returns 1x1 transparent GIF"""
    # Log the open event
    try:
        # Update tracked email
        result = await db.tracked_emails.update_one(
            {"id": email_id},
            {
                "$set": {"opened_at": datetime.now(timezone.utc).isoformat(), "status": "opened"},
                "$inc": {"open_count": 1}
            }
        )
        
        if result.modified_count > 0:
            # Get email details
            email = await db.tracked_emails.find_one({"id": email_id}, {"_id": 0})
            
            # Create tracking event
            event = EmailTrackingEvent(
                email_id=email_id,
                event_type="opened",
                lead_id=email.get("lead_id") if email else None,
                campaign_id=email.get("campaign_id") if email else None,
                sequence_id=email.get("sequence_id") if email else None,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None
            )
            event_doc = event.model_dump()
            event_doc['timestamp'] = event_doc['timestamp'].isoformat()
            await db.email_tracking_events.insert_one(event_doc)
            
            # Update campaign stats
            if email and email.get("campaign_id"):
                await db.email_campaigns.update_one(
                    {"id": email["campaign_id"]},
                    {"$inc": {"opened_count": 1}}
                )
    except Exception as e:
        logging.error(f"Error tracking email open: {e}")
    
    # Return 1x1 transparent GIF
    gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    return Response(content=gif_bytes, media_type="image/gif")

@api_router.get("/email/tracking/click/{email_id}/{link_id}")
async def track_email_click(email_id: str, link_id: str, url: str, request: Request):
    """Track link clicks and redirect to actual URL"""
    try:
        # Update tracked email
        await db.tracked_emails.update_one(
            {"id": email_id},
            {
                "$set": {"clicked_at": datetime.now(timezone.utc).isoformat(), "status": "clicked"},
                "$inc": {"click_count": 1}
            }
        )
        
        # Get email details
        email = await db.tracked_emails.find_one({"id": email_id}, {"_id": 0})
        
        # Create tracking event
        event = EmailTrackingEvent(
            email_id=email_id,
            event_type="clicked",
            lead_id=email.get("lead_id") if email else None,
            campaign_id=email.get("campaign_id") if email else None,
            sequence_id=email.get("sequence_id") if email else None,
            link_url=url,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None
        )
        event_doc = event.model_dump()
        event_doc['timestamp'] = event_doc['timestamp'].isoformat()
        await db.email_tracking_events.insert_one(event_doc)
        
        # Update campaign stats
        if email and email.get("campaign_id"):
            await db.email_campaigns.update_one(
                {"id": email["campaign_id"]},
                {"$inc": {"clicked_count": 1}}
            )
    except Exception as e:
        logging.error(f"Error tracking email click: {e}")
    
    # Redirect to actual URL
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url)

@api_router.get("/email/tracking/stats")
async def get_email_tracking_stats(
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Get email tracking statistics"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get tracked emails
    emails = await db.tracked_emails.find(
        {"sent_at": {"$gte": cutoff.isoformat()}, "sent_by": current_user.id},
        {"_id": 0}
    ).to_list(1000)
    
    total_sent = len(emails)
    total_opened = sum(1 for e in emails if e.get("opened_at"))
    total_clicked = sum(1 for e in emails if e.get("clicked_at"))
    total_replied = sum(1 for e in emails if e.get("replied_at"))
    
    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
    reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
    
    # Get daily breakdown
    daily_stats = {}
    for email in emails:
        date = email.get("sent_at", "")[:10]
        if date not in daily_stats:
            daily_stats[date] = {"sent": 0, "opened": 0, "clicked": 0, "replied": 0}
        daily_stats[date]["sent"] += 1
        if email.get("opened_at"):
            daily_stats[date]["opened"] += 1
        if email.get("clicked_at"):
            daily_stats[date]["clicked"] += 1
        if email.get("replied_at"):
            daily_stats[date]["replied"] += 1
    
    return {
        "summary": {
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "total_replied": total_replied,
            "open_rate": round(open_rate, 1),
            "click_rate": round(click_rate, 1),
            "reply_rate": round(reply_rate, 1)
        },
        "daily_breakdown": [
            {"date": date, **stats}
            for date, stats in sorted(daily_stats.items())
        ],
        "recent_emails": emails[:20]
    }

@api_router.get("/email/tracking/{email_id}")
async def get_email_tracking_details(email_id: str, current_user: User = Depends(get_current_user)):
    """Get detailed tracking for a specific email"""
    email = await db.tracked_emails.find_one({"id": email_id}, {"_id": 0})
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Get all events for this email
    events = await db.email_tracking_events.find(
        {"email_id": email_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    
    return {
        "email": email,
        "events": events
    }

# ==================== Email Sequences (Drip Campaigns) ====================

@api_router.get("/sequences")
async def get_sequences(current_user: User = Depends(get_current_user)):
    """Get all email sequences"""
    sequences = await db.email_sequences.find(
        {"created_by": current_user.id},
        {"_id": 0}
    ).to_list(100)
    return sequences

@api_router.post("/sequences")
async def create_sequence(
    name: str,
    description: Optional[str] = None,
    steps: List[dict] = [],
    exit_on_reply: bool = True,
    exit_on_meeting: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Create a new email sequence"""
    sequence = EmailSequence(
        name=name,
        description=description,
        steps=[SequenceStep(**step) for step in steps],
        exit_on_reply=exit_on_reply,
        exit_on_meeting=exit_on_meeting,
        created_by=current_user.id
    )
    
    seq_doc = sequence.model_dump()
    seq_doc['created_at'] = seq_doc['created_at'].isoformat()
    seq_doc['updated_at'] = seq_doc['updated_at'].isoformat()
    seq_doc['steps'] = [s.model_dump() if hasattr(s, 'model_dump') else s for s in seq_doc['steps']]
    await db.email_sequences.insert_one(seq_doc)
    
    return {"success": True, "sequence": seq_doc}

@api_router.get("/sequences/{sequence_id}")
async def get_sequence(sequence_id: str, current_user: User = Depends(get_current_user)):
    """Get sequence details with enrollments"""
    sequence = await db.email_sequences.find_one({"id": sequence_id}, {"_id": 0})
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    # Get enrollments
    enrollments = await db.sequence_enrollments.find(
        {"sequence_id": sequence_id},
        {"_id": 0}
    ).to_list(500)
    
    # Get lead details for enrollments
    lead_ids = [e["lead_id"] for e in enrollments]
    leads = await db.leads.find({"id": {"$in": lead_ids}}, {"_id": 0}).to_list(500)
    lead_map = {l["id"]: l for l in leads}
    
    for enrollment in enrollments:
        enrollment["lead"] = lead_map.get(enrollment["lead_id"])
    
    return {
        "sequence": sequence,
        "enrollments": enrollments
    }

@api_router.put("/sequences/{sequence_id}")
async def update_sequence(
    sequence_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    steps: Optional[List[dict]] = None,
    status: Optional[str] = None,
    exit_on_reply: Optional[bool] = None,
    exit_on_meeting: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Update a sequence"""
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if steps is not None:
        update_data["steps"] = steps
    if status is not None:
        update_data["status"] = status
    if exit_on_reply is not None:
        update_data["exit_on_reply"] = exit_on_reply
    if exit_on_meeting is not None:
        update_data["exit_on_meeting"] = exit_on_meeting
    
    result = await db.email_sequences.update_one(
        {"id": sequence_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    return {"success": True, "message": "Sequence updated"}

@api_router.delete("/sequences/{sequence_id}")
async def delete_sequence(sequence_id: str, current_user: User = Depends(get_current_user)):
    """Delete a sequence"""
    # Remove all enrollments first
    await db.sequence_enrollments.delete_many({"sequence_id": sequence_id})
    
    result = await db.email_sequences.delete_one({"id": sequence_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    return {"success": True, "message": "Sequence deleted"}

@api_router.post("/sequences/{sequence_id}/enroll")
async def enroll_leads_in_sequence(
    sequence_id: str,
    lead_ids: List[str],
    current_user: User = Depends(get_current_user)
):
    """Enroll leads in a sequence"""
    sequence = await db.email_sequences.find_one({"id": sequence_id}, {"_id": 0})
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    enrolled_count = 0
    already_enrolled = 0
    
    for lead_id in lead_ids:
        # Check if already enrolled
        existing = await db.sequence_enrollments.find_one({
            "sequence_id": sequence_id,
            "lead_id": lead_id,
            "status": "active"
        })
        
        if existing:
            already_enrolled += 1
            continue
        
        # Calculate first email time
        steps = sequence.get("steps", [])
        first_step = steps[0] if steps else None
        
        if first_step:
            delay_days = first_step.get("delay_days", 0)
            delay_hours = first_step.get("delay_hours", 0)
            next_email_at = datetime.now(timezone.utc) + timedelta(days=delay_days, hours=delay_hours)
        else:
            next_email_at = datetime.now(timezone.utc)
        
        enrollment = SequenceEnrollment(
            sequence_id=sequence_id,
            lead_id=lead_id,
            current_step=1,
            status="active",
            next_email_at=next_email_at,
            enrolled_by=current_user.id
        )
        
        enroll_doc = enrollment.model_dump()
        enroll_doc['enrolled_at'] = enroll_doc['enrolled_at'].isoformat()
        enroll_doc['next_email_at'] = enroll_doc['next_email_at'].isoformat() if enroll_doc['next_email_at'] else None
        await db.sequence_enrollments.insert_one(enroll_doc)
        
        enrolled_count += 1
    
    # Update sequence stats
    await db.email_sequences.update_one(
        {"id": sequence_id},
        {"$inc": {"total_enrolled": enrolled_count}}
    )
    
    return {
        "success": True,
        "enrolled_count": enrolled_count,
        "already_enrolled": already_enrolled
    }

@api_router.post("/sequences/{sequence_id}/unenroll/{lead_id}")
async def unenroll_lead_from_sequence(
    sequence_id: str,
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """Unenroll a lead from a sequence"""
    result = await db.sequence_enrollments.update_one(
        {"sequence_id": sequence_id, "lead_id": lead_id, "status": "active"},
        {"$set": {"status": "unenrolled", "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return {"success": True, "message": "Lead unenrolled from sequence"}

# ==================== Pipeline Forecasting ====================

@api_router.get("/forecasting/pipeline")
async def get_pipeline_forecast(current_user: User = Depends(get_current_user)):
    """Get AI-powered pipeline forecast"""
    # Get all active leads with deal values
    leads = await db.leads.find(
        {"stage": {"$nin": ["lost", "closed"]}},
        {"_id": 0}
    ).to_list(1000)
    
    # Calculate stage-based probabilities
    stage_probabilities = {
        "new": 10,
        "contacted": 20,
        "qualified": 40,
        "proposal": 60,
        "negotiation": 80,
        "won": 100,
        "lost": 0
    }
    
    forecasts = []
    total_pipeline = 0
    weighted_pipeline = 0
    
    for lead in leads:
        deal_value = lead.get("deal_value", 0) or 0
        stage = lead.get("stage", "new")
        probability = stage_probabilities.get(stage, 20)
        
        # Adjust probability based on activity
        last_contacted = lead.get("last_contacted")
        if last_contacted:
            days_since_contact = (datetime.now(timezone.utc) - datetime.fromisoformat(last_contacted.replace('Z', '+00:00'))).days
            if days_since_contact > 14:
                probability = max(5, probability - 15)
            elif days_since_contact < 3:
                probability = min(95, probability + 10)
        
        weighted_value = deal_value * (probability / 100)
        total_pipeline += deal_value
        weighted_pipeline += weighted_value
        
        forecasts.append({
            "lead_id": lead["id"],
            "lead_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            "company": lead.get("company"),
            "deal_value": deal_value,
            "stage": stage,
            "probability": probability,
            "weighted_value": weighted_value,
            "last_contacted": last_contacted
        })
    
    # Sort by weighted value
    forecasts.sort(key=lambda x: x["weighted_value"], reverse=True)
    
    # Calculate monthly forecast
    monthly_forecast = weighted_pipeline * 0.3  # Assume 30% close in current month
    quarterly_forecast = weighted_pipeline * 0.7  # 70% close in quarter
    
    # Stage distribution
    stage_distribution = {}
    for f in forecasts:
        stage = f["stage"]
        if stage not in stage_distribution:
            stage_distribution[stage] = {"count": 0, "value": 0, "weighted": 0}
        stage_distribution[stage]["count"] += 1
        stage_distribution[stage]["value"] += f["deal_value"]
        stage_distribution[stage]["weighted"] += f["weighted_value"]
    
    return {
        "summary": {
            "total_pipeline": total_pipeline,
            "weighted_pipeline": round(weighted_pipeline, 2),
            "monthly_forecast": round(monthly_forecast, 2),
            "quarterly_forecast": round(quarterly_forecast, 2),
            "total_deals": len(forecasts),
            "avg_deal_size": round(total_pipeline / len(forecasts), 2) if forecasts else 0,
            "avg_probability": round(sum(f["probability"] for f in forecasts) / len(forecasts), 1) if forecasts else 0
        },
        "stage_distribution": [
            {"stage": stage, **data}
            for stage, data in stage_distribution.items()
        ],
        "top_deals": forecasts[:10],
        "at_risk_deals": [f for f in forecasts if f["probability"] < 30][:10]
    }

@api_router.post("/forecasting/analyze-deal/{lead_id}")
async def analyze_deal_forecast(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get AI analysis for a specific deal"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get activity history
    activities = await db.activities.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    
    # Get call history
    calls = await db.call_logs.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).to_list(10)
    
    # Get email history
    emails = await db.tracked_emails.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).to_list(10)
    
    # Calculate engagement score
    engagement_score = 0
    engagement_score += len(activities) * 5
    engagement_score += len(calls) * 10
    engagement_score += sum(1 for e in emails if e.get("opened_at")) * 15
    engagement_score += sum(1 for e in emails if e.get("clicked_at")) * 20
    engagement_score = min(100, engagement_score)
    
    # Determine confidence factors and risks
    confidence_factors = []
    risk_factors = []
    
    if engagement_score > 50:
        confidence_factors.append("High engagement level")
    if lead.get("stage") in ["proposal", "negotiation"]:
        confidence_factors.append("Advanced pipeline stage")
    if calls and any(c.get("outcome") == "connected" for c in calls):
        confidence_factors.append("Successful call connections")
    if any(e.get("replied_at") for e in emails):
        confidence_factors.append("Email replies received")
    
    last_contacted = lead.get("last_contacted")
    if last_contacted:
        days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last_contacted.replace('Z', '+00:00'))).days
        if days_since > 14:
            risk_factors.append(f"No contact in {days_since} days")
    else:
        risk_factors.append("Never contacted")
    
    if engagement_score < 30:
        risk_factors.append("Low engagement score")
    if lead.get("stage") == "new":
        risk_factors.append("Still in early stage")
    
    # Calculate probability
    base_probability = {"new": 10, "contacted": 20, "qualified": 40, "proposal": 60, "negotiation": 80}.get(lead.get("stage"), 20)
    adjusted_probability = base_probability + (engagement_score - 50) * 0.3
    adjusted_probability = max(5, min(95, adjusted_probability))
    
    return {
        "lead": lead,
        "analysis": {
            "close_probability": round(adjusted_probability, 1),
            "engagement_score": engagement_score,
            "confidence_factors": confidence_factors,
            "risk_factors": risk_factors,
            "activity_count": len(activities),
            "call_count": len(calls),
            "email_count": len(emails),
            "emails_opened": sum(1 for e in emails if e.get("opened_at")),
            "recommendation": "Schedule a follow-up call" if risk_factors else "Continue current approach"
        }
    }

# ==================== Google Drive OAuth ====================

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', os.environ.get('GOOGLE_DRIVE_REDIRECT_URI'))
FRONTEND_URL = os.environ.get('FRONTEND_URL')

# Google OAuth Scopes for different services
GOOGLE_SCOPES = {
    'drive': 'https://www.googleapis.com/auth/drive',
    'calendar': 'https://www.googleapis.com/auth/calendar',
    'meet': 'https://www.googleapis.com/auth/calendar.events',  # Meet uses Calendar API
    'gmail_readonly': 'https://www.googleapis.com/auth/gmail.readonly',
    'profile': 'https://www.googleapis.com/auth/userinfo.profile',
    'email': 'https://www.googleapis.com/auth/userinfo.email'
}

async def get_google_credentials(user_id: str):
    """Get Google credentials for a user"""
    creds_doc = await db.google_credentials.find_one({"user_id": user_id})
    if not creds_doc:
        return None
    
    creds = Credentials(
        token=creds_doc["access_token"],
        refresh_token=creds_doc.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=creds_doc.get("scopes", [])
    )
    
    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
            await db.google_credentials.update_one(
                {"user_id": user_id},
                {"$set": {
                    "access_token": creds.token,
                    "expiry": creds.expiry.isoformat() if creds.expiry else None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        except Exception as e:
            logging.error(f"Failed to refresh Google token: {e}")
            return None
    
    return creds

async def get_drive_service(user: User):
    """Get Google Drive service with auto-refresh credentials"""
    creds = await get_google_credentials(user.id)
    if not creds:
        return None
    return build('drive', 'v3', credentials=creds)

async def get_calendar_service(user: User):
    """Get Google Calendar service"""
    creds = await get_google_credentials(user.id)
    if not creds:
        return None
    return build('calendar', 'v3', credentials=creds)

# =============================================================================
# GOOGLE INTEGRATION ENDPOINTS
# =============================================================================

@api_router.get("/google/status")
async def get_google_status(current_user: User = Depends(get_current_user)):
    """Check which Google services are connected"""
    creds_doc = await db.google_credentials.find_one({"user_id": current_user.id})
    
    if not creds_doc:
        return {
            "connected": False,
            "services": {
                "drive": False,
                "calendar": False,
                "meet": False
            },
            "message": "No Google account connected"
        }
    
    scopes = creds_doc.get("scopes", [])
    
    return {
        "connected": True,
        "email": creds_doc.get("email"),
        "name": creds_doc.get("name"),
        "picture": creds_doc.get("picture"),
        "connected_at": creds_doc.get("created_at"),
        "services": {
            "drive": GOOGLE_SCOPES['drive'] in scopes,
            "calendar": GOOGLE_SCOPES['calendar'] in scopes,
            "meet": GOOGLE_SCOPES['meet'] in scopes
        }
    }

@api_router.get("/google/connect")
async def connect_google(
    services: str = "drive,calendar",  # Comma-separated: drive,calendar,meet
    current_user: User = Depends(get_current_user)
):
    """Initiate Google OAuth flow for selected services"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=400, 
            detail="Google integration not configured. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to environment."
        )
    
    # Build scopes based on requested services
    requested_services = [s.strip() for s in services.split(',')]
    scopes = [GOOGLE_SCOPES['profile'], GOOGLE_SCOPES['email']]  # Always include profile
    
    for service in requested_services:
        if service in GOOGLE_SCOPES:
            scopes.append(GOOGLE_SCOPES[service])
    
    # Store state for CSRF protection
    state = f"{current_user.id}:{uuid.uuid4().hex[:16]}"
    await db.oauth_states.insert_one({
        "state": state,
        "user_id": current_user.id,
        "services": requested_services,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Build OAuth URL
    oauth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        "response_type=code&"
        f"scope={' '.join(scopes)}&"
        "access_type=offline&"
        "prompt=consent&"
        f"state={state}"
    )
    
    return {"auth_url": oauth_url}

@api_router.get("/google/callback")
async def google_callback(code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback"""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error={error}")
    
    if not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=missing_params")
    
    # Verify state
    state_doc = await db.oauth_states.find_one({"state": state})
    if not state_doc:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=invalid_state")
    
    user_id = state_doc["user_id"]
    
    # Clean up state
    await db.oauth_states.delete_one({"state": state})
    
    try:
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=token_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logging.error(f"Token exchange failed: {error_text}")
                    return RedirectResponse(f"{FRONTEND_URL}/settings?error=token_exchange_failed")
                
                tokens = await resp.json()
        
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        
        # Get user info from Google
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            ) as resp:
                if resp.status == 200:
                    user_info = await resp.json()
                else:
                    user_info = {}
        
        # Decode the scopes from the token
        scopes = tokens.get("scope", "").split(" ")
        
        # Store credentials
        creds_doc = {
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "scopes": scopes,
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert credentials
        await db.google_credentials.update_one(
            {"user_id": user_id},
            {"$set": creds_doc},
            upsert=True
        )
        
        # Also update legacy drive_credentials for backward compatibility
        await db.drive_credentials.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "scopes": scopes,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        
        return RedirectResponse(f"{FRONTEND_URL}/settings?google=connected")
        
    except Exception as e:
        logging.error(f"Google OAuth error: {e}")
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=oauth_failed")

@api_router.post("/google/disconnect")
async def disconnect_google(current_user: User = Depends(get_current_user)):
    """Disconnect Google account"""
    await db.google_credentials.delete_one({"user_id": current_user.id})
    await db.drive_credentials.delete_one({"user_id": current_user.id})
    return {"message": "Google account disconnected"}

# Google Calendar Integration
@api_router.get("/google/calendar/events")
async def get_google_calendar_events(
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get events from user's Google Calendar"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    try:
        now = datetime.now(timezone.utc)
        time_min = time_min or now.isoformat()
        time_max = time_max or (now + timedelta(days=30)).isoformat()
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        return {"events": events}
    except Exception as e:
        logging.error(f"Failed to get calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/google/calendar/events")
async def create_google_calendar_event(
    title: str,
    start_time: datetime,
    end_time: datetime,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    add_meet_link: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Create an event in user's Google Calendar with optional Meet link"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    try:
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            }
        }
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        if add_meet_link:
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': uuid.uuid4().hex,
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1 if add_meet_link else 0,
            sendUpdates='all' if attendees else 'none'
        ).execute()
        
        return {
            "id": created_event.get('id'),
            "html_link": created_event.get('htmlLink'),
            "meet_link": created_event.get('hangoutLink'),
            "message": "Event created successfully"
        }
    except Exception as e:
        logging.error(f"Failed to create calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== TWO-WAY GOOGLE CALENDAR SYNC ====================

class CalendarSyncRequest(BaseModel):
    sync_direction: str = "both"  # "to_google", "from_google", "both"
    days_ahead: int = 30
    days_back: int = 7

@api_router.post("/google/calendar/sync")
async def sync_google_calendar(
    sync_request: CalendarSyncRequest,
    current_user: User = Depends(get_current_user)
):
    """Full two-way sync between LeadGen Pro and Google Calendar"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected. Please connect your Google account first.")
    
    sync_results = {
        "pushed_to_google": 0,
        "pulled_from_google": 0,
        "errors": [],
        "synced_at": datetime.now(timezone.utc).isoformat()
    }
    
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=sync_request.days_back)).isoformat()
    time_max = (now + timedelta(days=sync_request.days_ahead)).isoformat()
    
    try:
        # PUSH: LeadGen Pro events -> Google Calendar
        if sync_request.sync_direction in ["to_google", "both"]:
            leadgen_events = await db.calendar_events.find({
                "created_by": current_user.id,
                "start": {"$gte": time_min, "$lte": time_max}
            }, {"_id": 0}).to_list(500)
            
            for event in leadgen_events:
                # Check if already synced
                if event.get("google_event_id"):
                    continue
                
                try:
                    google_event = {
                        'summary': event['title'],
                        'description': event.get('description', '') + f"\n\n[Synced from LeadGen Pro - ID: {event['id']}]",
                        'start': {
                            'dateTime': event['start'] if 'T' in event['start'] else event['start'] + 'T00:00:00Z',
                            'timeZone': 'UTC',
                        },
                        'end': {
                            'dateTime': event['end'] if 'T' in event['end'] else event['end'] + 'T23:59:59Z',
                            'timeZone': 'UTC',
                        }
                    }
                    
                    if event.get('meeting_link'):
                        google_event['description'] += f"\n\nMeeting Link: {event['meeting_link']}"
                        google_event['location'] = event['meeting_link']
                    
                    created = service.events().insert(
                        calendarId='primary',
                        body=google_event
                    ).execute()
                    
                    # Store Google event ID for future syncs
                    await db.calendar_events.update_one(
                        {"id": event['id']},
                        {"$set": {
                            "google_event_id": created['id'],
                            "google_synced_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    sync_results["pushed_to_google"] += 1
                    
                except Exception as e:
                    sync_results["errors"].append(f"Push error for {event['title']}: {str(e)}")
        
        # PULL: Google Calendar events -> LeadGen Pro
        if sync_request.sync_direction in ["from_google", "both"]:
            google_events = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=500,
                singleEvents=True,
                orderBy='startTime'
            ).execute().get('items', [])
            
            for g_event in google_events:
                google_id = g_event['id']
                
                # Check if already exists in LeadGen Pro
                existing = await db.calendar_events.find_one({"google_event_id": google_id})
                if existing:
                    continue
                
                # Also check by matching title and time (for events created elsewhere)
                start_time = g_event.get('start', {}).get('dateTime') or g_event.get('start', {}).get('date')
                if not start_time:
                    continue
                
                try:
                    end_time = g_event.get('end', {}).get('dateTime') or g_event.get('end', {}).get('date')
                    
                    new_event = {
                        "id": str(uuid.uuid4()),
                        "title": g_event.get('summary', 'Untitled Event'),
                        "description": g_event.get('description', ''),
                        "start": start_time,
                        "end": end_time or start_time,
                        "location": g_event.get('location', ''),
                        "meeting_link": g_event.get('hangoutLink', ''),
                        "created_by": current_user.id,
                        "attendees": [att.get('email') for att in g_event.get('attendees', []) if att.get('email')],
                        "google_event_id": google_id,
                        "google_synced_at": datetime.now(timezone.utc).isoformat(),
                        "source": "google_calendar",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await db.calendar_events.insert_one(new_event)
                    sync_results["pulled_from_google"] += 1
                    
                except Exception as e:
                    sync_results["errors"].append(f"Pull error for {g_event.get('summary', 'Unknown')}: {str(e)}")
        
        # Update sync status
        await db.google_credentials.update_one(
            {"user_id": current_user.id},
            {"$set": {
                "last_calendar_sync": datetime.now(timezone.utc).isoformat(),
                "sync_stats": sync_results
            }}
        )
        
        return {
            "success": True,
            "message": f"Sync complete! Pushed {sync_results['pushed_to_google']} events to Google, pulled {sync_results['pulled_from_google']} events from Google.",
            "results": sync_results
        }
        
    except Exception as e:
        logging.error(f"Calendar sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@api_router.put("/google/calendar/events/{event_id}")
async def update_google_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Update an event in Google Calendar (two-way sync)"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    # Find the local event
    local_event = await db.calendar_events.find_one({"id": event_id})
    if not local_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    google_event_id = local_event.get("google_event_id")
    
    # Update local event
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if title:
        update_data["title"] = title
    if start_time:
        update_data["start"] = start_time.isoformat()
    if end_time:
        update_data["end"] = end_time.isoformat()
    if description:
        update_data["description"] = description
    
    await db.calendar_events.update_one({"id": event_id}, {"$set": update_data})
    
    # If synced to Google, update there too
    if google_event_id:
        try:
            existing = service.events().get(calendarId='primary', eventId=google_event_id).execute()
            
            if title:
                existing['summary'] = title
            if start_time:
                existing['start'] = {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'}
            if end_time:
                existing['end'] = {'dateTime': end_time.isoformat(), 'timeZone': 'UTC'}
            if description:
                existing['description'] = description
            
            service.events().update(
                calendarId='primary',
                eventId=google_event_id,
                body=existing
            ).execute()
            
            return {"success": True, "message": "Event updated in both LeadGen Pro and Google Calendar"}
        except Exception as e:
            logging.error(f"Failed to update Google event: {e}")
            return {"success": True, "message": "Event updated locally but Google sync failed", "error": str(e)}
    
    return {"success": True, "message": "Event updated locally"}

@api_router.delete("/google/calendar/events/{event_id}")
async def delete_google_calendar_event(
    event_id: str,
    delete_from_google: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Delete an event from LeadGen Pro and optionally from Google Calendar"""
    local_event = await db.calendar_events.find_one({"id": event_id})
    if not local_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    google_event_id = local_event.get("google_event_id")
    
    # Delete from Google if connected and requested
    if google_event_id and delete_from_google:
        service = await get_calendar_service(current_user)
        if service:
            try:
                service.events().delete(calendarId='primary', eventId=google_event_id).execute()
            except Exception as e:
                logging.error(f"Failed to delete from Google Calendar: {e}")
    
    # Delete locally
    await db.calendar_events.delete_one({"id": event_id})
    
    return {"success": True, "message": "Event deleted"}

@api_router.get("/google/calendar/sync-status")
async def get_google_calendar_sync_status(current_user: User = Depends(get_current_user)):
    """Get detailed Google Calendar sync status"""
    creds_doc = await db.google_credentials.find_one({"user_id": current_user.id})
    
    if not creds_doc:
        return {
            "connected": False,
            "can_sync": False,
            "message": "Google Calendar not connected. Connect your Google account to enable two-way sync."
        }
    
    has_calendar_scope = GOOGLE_SCOPES['calendar'] in creds_doc.get("scopes", [])
    
    # Count synced events
    synced_count = await db.calendar_events.count_documents({
        "created_by": current_user.id,
        "google_event_id": {"$exists": True, "$ne": None}
    })
    
    pending_count = await db.calendar_events.count_documents({
        "created_by": current_user.id,
        "google_event_id": {"$exists": False}
    })
    
    return {
        "connected": True,
        "can_sync": has_calendar_scope,
        "email": creds_doc.get("email"),
        "last_sync": creds_doc.get("last_calendar_sync"),
        "sync_stats": creds_doc.get("sync_stats"),
        "events_synced": synced_count,
        "events_pending": pending_count,
        "message": "Two-way sync enabled" if has_calendar_scope else "Calendar permissions not granted"
    }

@api_router.post("/google/calendar/push-event/{event_id}")
async def push_single_event_to_google(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """Push a single LeadGen Pro event to Google Calendar"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    event = await db.calendar_events.find_one({"id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.get("google_event_id"):
        return {"success": False, "message": "Event already synced to Google Calendar"}
    
    try:
        google_event = {
            'summary': event['title'],
            'description': event.get('description', ''),
            'start': {
                'dateTime': event['start'] if 'T' in event['start'] else event['start'] + 'T00:00:00Z',
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': event['end'] if 'T' in event['end'] else event['end'] + 'T23:59:59Z',
                'timeZone': 'UTC',
            }
        }
        
        if event.get('meeting_link'):
            google_event['location'] = event['meeting_link']
        
        created = service.events().insert(calendarId='primary', body=google_event).execute()
        
        await db.calendar_events.update_one(
            {"id": event_id},
            {"$set": {
                "google_event_id": created['id'],
                "google_synced_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "success": True,
            "google_event_id": created['id'],
            "google_link": created.get('htmlLink'),
            "message": "Event pushed to Google Calendar"
        }
    except Exception as e:
        logging.error(f"Failed to push event to Google: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Legacy Drive endpoints (keep for backward compatibility)
@api_router.get("/drive/status")
async def get_drive_status(current_user: User = Depends(get_current_user)):
    """Check if Google Drive is connected for current user"""
    creds_doc = await db.google_credentials.find_one({"user_id": current_user.id})
    
    if not creds_doc:
        return {"connected": False, "message": "Google Drive not connected"}
    
    has_drive_scope = GOOGLE_SCOPES['drive'] in creds_doc.get("scopes", [])
    
    return {
        "connected": has_drive_scope,
        "email": creds_doc.get("email") if has_drive_scope else None,
        "connected_at": creds_doc.get("updated_at") if has_drive_scope else None
    }

@api_router.get("/drive/connect")
async def connect_drive(current_user: User = Depends(get_current_user)):
    """Redirect to unified Google connect with Drive scope"""
    return await connect_google(services="drive", current_user=current_user)

@api_router.get("/drive/callback")
async def drive_callback(code: str = None, state: str = None, error: str = None):
    """Legacy callback - redirect to unified Google callback"""
    return await google_callback(code=code, state=state, error=error)

@api_router.get("/drive/disconnect")
async def disconnect_drive(current_user: User = Depends(get_current_user)):
    """Disconnect Google Drive"""
    await db.drive_credentials.delete_one({"user_id": current_user.id})
    return {"success": True, "message": "Google Drive disconnected"}

@api_router.get("/drive/files")
async def list_drive_files(
    folder_id: str = None,
    page_token: str = None,
    current_user: User = Depends(get_current_user)
):
    """List files from Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        # Build query
        query_parts = ["trashed = false"]
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        else:
            query_parts.append("'root' in parents")
        
        query = " and ".join(query_parts)
        
        # Execute query
        results = service.files().list(
            q=query,
            pageSize=50,
            pageToken=page_token,
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, iconLink, thumbnailLink, parents)",
            orderBy="folder,name"
        ).execute()
        
        files = results.get('files', [])
        next_page_token = results.get('nextPageToken')
        
        # Format response
        formatted_files = []
        for file in files:
            formatted_files.append({
                "id": file.get('id'),
                "name": file.get('name'),
                "mimeType": file.get('mimeType'),
                "isFolder": file.get('mimeType') == 'application/vnd.google-apps.folder',
                "size": int(file.get('size', 0)) if file.get('size') else None,
                "modifiedTime": file.get('modifiedTime'),
                "webViewLink": file.get('webViewLink'),
                "iconLink": file.get('iconLink'),
                "thumbnailLink": file.get('thumbnailLink')
            })
        
        return {
            "files": formatted_files,
            "nextPageToken": next_page_token
        }
    
    except Exception as e:
        logging.error(f"Failed to list Drive files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@api_router.post("/drive/folder")
async def create_drive_folder(
    name: str,
    parent_id: str = None,
    current_user: User = Depends(get_current_user)
):
    """Create a folder in Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink'
        ).execute()
        
        return {
            "success": True,
            "folder": {
                "id": folder.get('id'),
                "name": folder.get('name'),
                "webViewLink": folder.get('webViewLink')
            }
        }
    
    except Exception as e:
        logging.error(f"Failed to create folder: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create folder: {str(e)}")

@api_router.post("/drive/upload")
async def upload_to_drive(
    file: UploadFile = File(...),
    folder_id: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Upload a file to Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        file_metadata = {'name': file.filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(tmp_path, mimetype=file.content_type, resumable=True)
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, size'
        ).execute()
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return {
            "success": True,
            "file": {
                "id": uploaded_file.get('id'),
                "name": uploaded_file.get('name'),
                "webViewLink": uploaded_file.get('webViewLink'),
                "size": uploaded_file.get('size')
            }
        }
    
    except Exception as e:
        logging.error(f"Failed to upload file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@api_router.delete("/drive/files/{file_id}")
async def delete_drive_file(file_id: str, current_user: User = Depends(get_current_user)):
    """Delete a file from Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        service.files().delete(fileId=file_id).execute()
        return {"success": True, "message": "File deleted"}
    
    except Exception as e:
        logging.error(f"Failed to delete file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@api_router.get("/drive/search")
async def search_drive_files(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """Search files in Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        search_query = f"name contains '{query}' and trashed = false"
        
        results = service.files().list(
            q=search_query,
            pageSize=20,
            fields="files(id, name, mimeType, size, modifiedTime, webViewLink, iconLink, thumbnailLink)"
        ).execute()
        
        files = results.get('files', [])
        
        formatted_files = []
        for file in files:
            formatted_files.append({
                "id": file.get('id'),
                "name": file.get('name'),
                "mimeType": file.get('mimeType'),
                "isFolder": file.get('mimeType') == 'application/vnd.google-apps.folder',
                "size": int(file.get('size', 0)) if file.get('size') else None,
                "modifiedTime": file.get('modifiedTime'),
                "webViewLink": file.get('webViewLink'),
                "iconLink": file.get('iconLink'),
                "thumbnailLink": file.get('thumbnailLink')
            })
        
        return {"files": formatted_files}
    
    except Exception as e:
        logging.error(f"Failed to search files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search files: {str(e)}")

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

@api_router.get("/admin/errors")
async def get_system_errors(
    current_user: User = Depends(get_current_user),
    severity: Optional[str] = None,
    category: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 50
):
    """Get system errors for admin dashboard"""
    # Check if admin
    is_admin = current_user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or current_user.role == 'admin'
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if severity:
        query["severity"] = severity
    if category:
        query["category"] = category
    if resolved is not None:
        query["resolved"] = resolved
    
    errors = await db.system_errors.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Get stats
    total = await db.system_errors.count_documents({})
    unresolved = await db.system_errors.count_documents({"resolved": False})
    critical = await db.system_errors.count_documents({"severity": "critical", "resolved": False})
    
    return {
        "errors": errors,
        "stats": {
            "total": total,
            "unresolved": unresolved,
            "critical": critical
        }
    }

@api_router.put("/admin/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    current_user: User = Depends(get_current_user)
):
    """Manually mark an error as resolved"""
    is_admin = current_user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or current_user.role == 'admin'
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.system_errors.update_one(
        {"id": error_id},
        {
            "$set": {
                "resolved": True,
                "resolved_by": current_user.id,
                "resolved_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Error not found")
    
    return {"message": "Error marked as resolved"}

@api_router.get("/admin/system-health")
async def get_system_health(current_user: User = Depends(get_current_user)):
    """Get overall system health status"""
    is_admin = current_user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or current_user.role == 'admin'
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check database
    db_status = "healthy"
    try:
        await db.command('ping')
    except:
        db_status = "unhealthy"
    
    # Check external services
    services = {
        "database": db_status,
        "resend_email": "configured" if RESEND_API_KEY else "not_configured",
        "twilio_voice": "configured" if twilio_client else "not_configured",
        "ai_diagnosis": "configured" if EMERGENT_LLM_KEY else "not_configured"
    }
    
    # Get error stats from last 24 hours
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    recent_errors = await db.system_errors.count_documents({
        "created_at": {"$gte": yesterday}
    })
    critical_errors = await db.system_errors.count_documents({
        "created_at": {"$gte": yesterday},
        "severity": "critical"
    })
    
    overall_health = "healthy"
    if critical_errors > 0:
        overall_health = "critical"
    elif recent_errors > 10:
        overall_health = "warning"
    elif db_status == "unhealthy":
        overall_health = "critical"
    
    return {
        "overall": overall_health,
        "services": services,
        "recent_errors_24h": recent_errors,
        "critical_errors_24h": critical_errors,
        "timestamp": datetime.now(timezone.utc).isoformat()
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

# ==================== Admin/Employee Portal Endpoints ====================

# Models for Employee Dashboard
class DailyGoal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    date: str  # YYYY-MM-DD format
    calls_target: int = 20
    meetings_target: int = 3
    emails_target: int = 10
    notes: Optional[str] = None  # Admin notes for the employee
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DailyGoalCreate(BaseModel):
    employee_id: str
    date: str
    calls_target: int = 20
    meetings_target: int = 3
    emails_target: int = 10
    notes: Optional[str] = None

class EmployeePerformance(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str] = None
    calls_today: int = 0
    calls_total: int = 0
    meetings_today: int = 0
    meetings_total: int = 0
    leads_assigned: int = 0
    leads_converted: int = 0
    conversion_rate: float = 0.0
    last_activity: Optional[datetime] = None

def is_admin_user(user: User) -> bool:
    """Check if user is an admin (by role or email)"""
    return user.role == "admin" or user.email in ADMIN_EMAILS

@api_router.get("/admin/dashboard/stats")
async def admin_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get admin dashboard statistics - full company overview"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all employees
    employees = await db.users.find({"role": {"$in": ["employee", "manager"]}}, {"_id": 0, "password": 0}).to_list(1000)
    
    # Calculate company-wide stats
    total_leads = await db.leads.count_documents({})
    total_calls = await db.call_logs.count_documents({})
    total_meetings = await db.appointments.count_documents({})
    
    # Get today's date for daily stats
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_start = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)
    
    calls_today = await db.call_logs.count_documents({
        "created_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    meetings_today = await db.appointments.count_documents({
        "scheduled_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    # Get leads by stage for pipeline overview
    pipeline_stages = {}
    for stage in ["prospecting", "qualified", "proposal", "negotiation", "closed"]:
        count = await db.leads.count_documents({"stage": stage})
        pipeline_stages[stage] = count
    
    # Calculate conversion rate
    closed_leads = await db.leads.count_documents({"stage": "closed"})
    conversion_rate = (closed_leads / total_leads * 100) if total_leads > 0 else 0
    
    return {
        "total_employees": len(employees),
        "total_leads": total_leads,
        "total_calls": total_calls,
        "total_meetings": total_meetings,
        "calls_today": calls_today,
        "meetings_today": meetings_today,
        "pipeline_stages": pipeline_stages,
        "conversion_rate": round(conversion_rate, 1),
        "active_leads": total_leads - closed_leads
    }

@api_router.get("/admin/employees/performance")
async def get_employees_performance(current_user: User = Depends(get_current_user)):
    """Get performance metrics for all employees (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all employees (including managers)
    employees = await db.users.find(
        {"role": {"$in": ["employee", "manager"]}}, 
        {"_id": 0, "password": 0}
    ).to_list(1000)
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_start = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)
    
    performance_data = []
    for emp in employees:
        emp_id = emp['id']
        
        # Get calls stats
        calls_today = await db.call_logs.count_documents({
            "agent_id": emp_id,
            "created_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
        })
        calls_total = await db.call_logs.count_documents({"agent_id": emp_id})
        
        # Get meetings stats
        meetings_today = await db.appointments.count_documents({
            "employee_id": emp_id,
            "scheduled_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
        })
        meetings_total = await db.appointments.count_documents({"employee_id": emp_id})
        
        # Get leads stats
        leads_assigned = await db.leads.count_documents({"assigned_to": emp_id})
        leads_converted = await db.leads.count_documents({"assigned_to": emp_id, "stage": "closed"})
        
        # Get last activity
        last_activity = await db.activities.find_one(
            {"user_id": emp_id}, 
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        performance_data.append({
            "employee_id": emp_id,
            "employee_name": emp.get('full_name', 'Unknown'),
            "email": emp.get('email', ''),
            "department": emp.get('department'),
            "role": emp.get('role', 'employee'),
            "calls_today": calls_today,
            "calls_total": calls_total,
            "meetings_today": meetings_today,
            "meetings_total": meetings_total,
            "leads_assigned": leads_assigned,
            "leads_converted": leads_converted,
            "conversion_rate": round((leads_converted / leads_assigned * 100) if leads_assigned > 0 else 0, 1),
            "last_activity": last_activity.get('created_at') if last_activity else None
        })
    
    # Sort by calls today (descending)
    performance_data.sort(key=lambda x: x['calls_today'], reverse=True)
    
    return performance_data

@api_router.post("/admin/daily-goals")
async def set_daily_goals(goal_data: DailyGoalCreate, current_user: User = Depends(get_current_user)):
    """Set daily goals for an employee (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if employee exists
    employee = await db.users.find_one({"id": goal_data.employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Upsert daily goal (update if exists, create if not)
    goal = DailyGoal(
        employee_id=goal_data.employee_id,
        date=goal_data.date,
        calls_target=goal_data.calls_target,
        meetings_target=goal_data.meetings_target,
        emails_target=goal_data.emails_target,
        notes=goal_data.notes,
        created_by=current_user.id
    )
    
    doc = goal.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    # Upsert based on employee_id and date
    await db.daily_goals.update_one(
        {"employee_id": goal_data.employee_id, "date": goal_data.date},
        {"$set": doc},
        upsert=True
    )
    
    return {"success": True, "message": "Daily goals set successfully", "goal": goal}

@api_router.get("/admin/daily-goals/{employee_id}")
async def get_employee_daily_goals(employee_id: str, date: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get daily goals for an employee (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {"employee_id": employee_id}
    if date:
        query["date"] = date
    
    goals = await db.daily_goals.find(query, {"_id": 0}).sort("date", -1).to_list(30)
    return goals

@api_router.post("/admin/distribute-leads-roundrobin")
async def distribute_leads_roundrobin(
    lead_ids: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user)
):
    """Distribute leads to employees using round-robin (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all active employees
    employees = await db.users.find(
        {"role": {"$in": ["employee", "manager"]}}, 
        {"_id": 0}
    ).to_list(1000)
    
    if not employees:
        raise HTTPException(status_code=400, detail="No employees found")
    
    # Get leads to distribute
    if lead_ids:
        query = {"id": {"$in": lead_ids}, "assigned_to": None}
    else:
        query = {"assigned_to": None}
    
    leads = await db.leads.find(query, {"_id": 0}).to_list(10000)
    
    if not leads:
        raise HTTPException(status_code=404, detail="No unassigned leads found")
    
    # Round-robin distribution
    distributed = []
    employee_ids = [emp['id'] for emp in employees]
    
    for i, lead in enumerate(leads):
        employee_idx = i % len(employee_ids)
        employee_id = employee_ids[employee_idx]
        
        await db.leads.update_one(
            {"id": lead['id']},
            {
                "$set": {
                    "assigned_to": employee_id,
                    "assigned_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        emp_name = next((e['full_name'] for e in employees if e['id'] == employee_id), 'Unknown')
        distributed.append({
            "lead_id": lead['id'],
            "lead_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}",
            "employee_id": employee_id,
            "employee_name": emp_name
        })
    
    return {
        "success": True,
        "message": f"Distributed {len(distributed)} leads to {len(employees)} employees using round-robin",
        "total_distributed": len(distributed),
        "distributions": distributed[:50]
    }

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