from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, UploadFile, File, Form
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
    company: str
    title: Optional[str] = None
    status: str = "new"
    stage: str = "prospecting"
    score: int = 0
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
    company: str
    title: Optional[str] = None
    status: str = "new"
    tags: List[str] = []

class Appointment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    lead_id: str
    employee_id: str
    scheduled_at: datetime
    duration: int = 30
    status: str = "scheduled"
    meeting_link: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AppointmentCreate(BaseModel):
    title: str
    lead_id: str
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
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    lead_id: str
    phone_number: str
    outcome: str
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
    lead_id: str
    phone_number: str
    outcome: str
    duration: int = 0
    notes: Optional[str] = None
    call_sid: Optional[str] = None

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

# Auth routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.model_dump(exclude={"password"})
    user = User(**user_dict)
    
    doc = user.model_dump()
    doc['password'] = get_password_hash(user_data.password)
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user_doc['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**{k: v for k, v in user_doc.items() if k != 'password'})
    
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.put("/auth/onboarding")
async def complete_onboarding(current_user: User = Depends(get_current_user)):
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"onboarding_completed": True}}
    )
    return {"message": "Onboarding completed"}

# Leads routes
@api_router.get("/leads", response_model=List[Lead])
async def get_leads(stage: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {}
    if current_user.role == "employee":
        query["assigned_to"] = current_user.id
    elif current_user.role == "client":
        query["created_by"] = current_user.id
    
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

# Bulk Import
class BulkImportResult(BaseModel):
    success: int
    failed: int
    errors: List[str] = []

@api_router.post("/leads/bulk-import", response_model=BulkImportResult)
async def bulk_import_leads(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
):
    """Import leads from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    contents = await file.read()
    csv_data = csv.DictReader(io.StringIO(contents.decode('utf-8')))
    
    success_count = 0
    failed_count = 0
    errors = []
    
    for row_num, row in enumerate(csv_data, start=2):
        try:
            # Map CSV columns to lead fields
            lead_data = {
                'first_name': row.get('first_name') or row.get('First Name') or row.get('FirstName', '').strip(),
                'last_name': row.get('last_name') or row.get('Last Name') or row.get('LastName', '').strip(),
                'email': row.get('email') or row.get('Email', '').strip(),
                'phone': row.get('phone') or row.get('Phone') or row.get('PhoneNumber', '').strip(),
                'company': row.get('company') or row.get('Company', '').strip(),
                'title': row.get('title') or row.get('Title') or row.get('JobTitle', '').strip(),
                'status': 'new',
                'tags': []
            }
            
            # Validate required fields
            if not lead_data['first_name'] or not lead_data['last_name'] or not lead_data['email'] or not lead_data['company']:
                errors.append(f"Row {row_num}: Missing required fields")
                failed_count += 1
                continue
            
            # Create lead
            lead_data['created_by'] = current_user.id
            lead_data['score'] = await calculate_lead_score(lead_data)
            
            lead = Lead(**lead_data)
            doc = lead.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            
            await db.leads.insert_one(doc)
            success_count += 1
            
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            failed_count += 1
    
    return BulkImportResult(
        success=success_count,
        failed=failed_count,
        errors=errors[:10]  # Return first 10 errors
    )

# Website Scraper
class ScrapeRequest(BaseModel):
    url: str
    selectors: Optional[Dict[str, str]] = None

class ScrapedContact(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None

@api_router.post("/leads/scrape")
async def scrape_website(
    request: ScrapeRequest,
    current_user: User = Depends(get_current_user)
):
    """Scrape contact information from a website"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(request.url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, html)
        emails = list(set([e for e in emails if not e.endswith(('.png', '.jpg', '.gif'))]))[:20]
        
        # Extract phone numbers
        phone_pattern = r'\+?1?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
        phones = re.findall(phone_pattern, html)
        phones = list(set(phones))[:10]
        
        # Extract company name from title or h1
        company = None
        title_tag = soup.find('title')
        if title_tag:
            company = title_tag.text.strip().split('|')[0].strip()
        
        # Create leads from scraped data
        created_leads = []
        for i, email in enumerate(emails):
            name_parts = email.split('@')[0].split('.')
            first_name = name_parts[0].capitalize() if name_parts else 'Unknown'
            last_name = name_parts[1].capitalize() if len(name_parts) > 1 else 'Contact'
            
            lead_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phones[i] if i < len(phones) else None,
                'company': company or 'Scraped Company',
                'title': 'Contact',
                'status': 'new',
                'tags': ['scraped'],
                'created_by': current_user.id
            }
            
            lead_data['score'] = await calculate_lead_score(lead_data)
            lead = Lead(**lead_data)
            doc = lead.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            
            await db.leads.insert_one(doc)
            created_leads.append(lead)
        
        return {
            "message": f"Scraped {len(created_leads)} contacts from website",
            "contacts_found": len(emails),
            "leads_created": len(created_leads),
            "url": request.url
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

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
    type: str = "public"  # public, private
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "public"

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
    """Get all channels"""
    channels = await db.channels.find({}, {"_id": 0}).to_list(1000)
    
    # Create default channels if none exist
    if not channels:
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
        
        channels = await db.channels.find({}, {"_id": 0}).to_list(1000)
    
    return [Channel(**ch) for ch in channels]

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

@api_router.post("/voice/call")
async def initiate_call(
    phone_number: str,
    lead_id: str,
    record: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Initiate an outbound call through Twilio"""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    try:
        # Format phone number to E.164
        formatted_number = phone_number
        if not formatted_number.startswith('+'):
            # Assume US number if no country code
            formatted_number = '+1' + re.sub(r'\D', '', formatted_number)
        
        # Create the call with optional recording
        call_params = {
            'to': formatted_number,
            'from_': TWILIO_PHONE_NUMBER,
            'twiml': '<Response><Say>Connecting you now. Please hold.</Say><Dial>' + formatted_number + '</Dial></Response>',
            'timeout': 60
        }
        
        # Enable recording if requested
        if record:
            call_params['record'] = True
            call_params['recording_status_callback'] = f"{os.environ.get('REACT_APP_BACKEND_URL', '')}/api/voice/recording-callback"
        
        call = twilio_client.calls.create(**call_params)
        
        # Log the call initiation activity
        activity = Activity(
            type="call_initiated",
            description=f"Initiated {'recorded ' if record else ''}call to {formatted_number}",
            lead_id=lead_id,
            user_id=current_user.id,
            metadata={"call_sid": call.sid, "phone_number": formatted_number, "recorded": record}
        )
        activity_doc = activity.model_dump()
        activity_doc['created_at'] = activity_doc['created_at'].isoformat()
        await db.activities.insert_one(activity_doc)
        
        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status,
            "to": formatted_number,
            "from": TWILIO_PHONE_NUMBER,
            "recording": record
        }
    except Exception as e:
        logging.error(f"Error initiating call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@api_router.post("/booking/{user_id}/book")
async def create_booking(user_id: str, booking: BookingRequest):
    """Create a booking (public endpoint - no auth required)"""
    # Verify user exists
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if slot is available
    booking_start = booking.datetime
    booking_end = booking_start + timedelta(minutes=booking.duration)
    
    # Look for conflicting events
    conflict = await db.calendar_events.find_one({
        "$or": [
            {"created_by": user_id},
            {"attendees": user_id}
        ],
        "$or": [
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
    email_sent = False
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
        email_sent = email_result is not None
    
    return {
        "success": True,
        "event_id": event.id,
        "message": "Meeting booked successfully",
        "email_notification_sent": email_sent,
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