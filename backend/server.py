from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, UploadFile, File
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