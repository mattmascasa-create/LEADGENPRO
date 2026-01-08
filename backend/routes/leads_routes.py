"""
LeadGen Pro - Lead Management Routes
Handles lead CRUD, bulk import, and lead distribution
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from jose import JWTError, jwt
import uuid
import csv
import io
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

router = APIRouter(prefix="/leads", tags=["Leads"])
logger = logging.getLogger(__name__)

# Database connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'leadgenpro')]

# Security
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Admin emails
ADMIN_EMAILS = ['mattmascasa@gmail.com', 'monika.iordanoff@gmail.com', 'admin@test.com']

# ==================== User Model ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    role: str
    company: Optional[str] = None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials"
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise credentials_exception
    return User(**user)

def is_admin(user: User) -> bool:
    return user.email.lower() in [e.lower() for e in ADMIN_EMAILS] or user.role == 'admin'

async def log_activity(activity_type: str, description: str, user_id: str, lead_id: str = None):
    """Log an activity to the database"""
    activity = {
        "id": str(uuid.uuid4()),
        "type": activity_type,
        "description": description,
        "user_id": user_id,
        "lead_id": lead_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.activities.insert_one(activity)

# ==================== Request Models ====================

class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    company: str
    title: Optional[str] = None
    status: str = "new"
    tags: List[str] = []

class Lead(BaseModel):
    id: str
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
    created_at: datetime
    updated_at: datetime

class BulkImportResult(BaseModel):
    imported: int
    skipped: int
    errors: List[str] = []

# ==================== AI Functions ====================

async def generate_ai_insight(lead_data: dict) -> str:
    """Generate AI insights for a lead"""
    if not EMERGENT_LLM_KEY:
        return "AI insights unavailable - API key not configured"
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, model="anthropic/claude-sonnet-4-20250514")
        prompt = f"""Analyze this lead and provide brief sales insights (2-3 sentences):
        Name: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}
        Company: {lead_data.get('company', '')}
        Title: {lead_data.get('title', '')}
        Focus on: best approach, potential value, and engagement strategy."""
        
        response = await chat.send_message_async(message=UserMessage(content=prompt))
        return response.content
    except Exception as e:
        logger.error(f"AI insight error: {e}")
        return "AI insights temporarily unavailable"

async def calculate_lead_score(lead_data: dict) -> int:
    """Calculate lead score based on various factors"""
    score = 50  # Base score
    
    if lead_data.get('title'):
        title_lower = lead_data['title'].lower()
        if any(t in title_lower for t in ['ceo', 'cto', 'cfo', 'president', 'owner']):
            score += 30
        elif any(t in title_lower for t in ['director', 'vp', 'head']):
            score += 20
        elif any(t in title_lower for t in ['manager', 'lead']):
            score += 10
    
    if lead_data.get('phone'):
        score += 10
    
    if lead_data.get('company'):
        score += 5
    
    return min(score, 100)

# ==================== Endpoints ====================

@router.get("", response_model=List[Lead])
async def get_leads(stage: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get all leads (filtered by user if not admin)"""
    query = {}
    
    # Non-admin users can only see their own leads
    if not is_admin(current_user):
        query["$or"] = [
            {"assigned_to": current_user.id},
            {"created_by": current_user.id}
        ]
    
    if stage:
        query["stage"] = stage
    
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return leads


@router.post("", response_model=Lead)
async def create_lead(lead_data: LeadCreate, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    """Create a new lead"""
    lead_dict = lead_data.model_dump()
    lead_dict["id"] = str(uuid.uuid4())
    lead_dict["created_by"] = current_user.id
    lead_dict["assigned_to"] = current_user.id
    lead_dict["stage"] = "prospecting"
    lead_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    lead_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Calculate score and generate AI insights in background
    lead_dict["score"] = await calculate_lead_score(lead_dict)
    
    await db.leads.insert_one(lead_dict)
    
    # Generate AI insights asynchronously
    async def generate_insights():
        insights = await generate_ai_insight(lead_dict)
        await db.leads.update_one({"id": lead_dict["id"]}, {"$set": {"ai_insights": insights}})
    
    background_tasks.add_task(generate_insights)
    
    # Log activity
    await log_activity(
        "lead_created",
        f"Created lead: {lead_data.first_name} {lead_data.last_name}",
        current_user.id,
        lead_dict["id"]
    )
    
    lead_dict.pop("_id", None)
    return lead_dict


@router.get("/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific lead by ID"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/{lead_id}", response_model=Lead)
async def update_lead(lead_id: str, lead_data: LeadCreate, current_user: User = Depends(get_current_user)):
    """Update a lead"""
    update_dict = lead_data.model_dump()
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_dict["score"] = await calculate_lead_score(update_dict)
    
    result = await db.leads.update_one({"id": lead_id}, {"$set": update_dict})
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return lead


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Delete a lead"""
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted"}


@router.post("/{lead_id}/stage")
async def update_lead_stage(lead_id: str, stage: str, current_user: User = Depends(get_current_user)):
    """Update lead stage in pipeline"""
    valid_stages = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    
    result = await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"stage": stage, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    await log_activity(
        "stage_changed",
        f"Moved lead to {stage}",
        current_user.id,
        lead_id
    )
    
    return {"message": "Stage updated", "stage": stage}


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_leads(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Bulk import leads from CSV file"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    csv_reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
    
    imported = 0
    skipped = 0
    errors = []
    
    for row in csv_reader:
        try:
            # Map CSV columns to lead fields
            first_name = row.get('first_name') or row.get('First Name') or row.get('firstName', '')
            last_name = row.get('last_name') or row.get('Last Name') or row.get('lastName', '')
            email = row.get('email') or row.get('Email', '')
            phone = row.get('phone') or row.get('Phone', '')
            company = row.get('company') or row.get('Company', '')
            title = row.get('title') or row.get('Title', '')
            
            if not email or not first_name:
                skipped += 1
                continue
            
            # Check for existing lead
            existing = await db.leads.find_one({"email": email.lower()})
            if existing:
                skipped += 1
                continue
            
            lead = {
                "id": str(uuid.uuid4()),
                "first_name": first_name,
                "last_name": last_name,
                "email": email.lower(),
                "phone": phone,
                "company": company,
                "title": title,
                "status": "new",
                "stage": "prospecting",
                "score": 50,
                "created_by": current_user.id,
                "assigned_to": current_user.id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "tags": []
            }
            
            await db.leads.insert_one(lead)
            imported += 1
            
        except Exception as e:
            errors.append(str(e))
    
    await log_activity(
        "bulk_import",
        f"Imported {imported} leads from CSV",
        current_user.id
    )
    
    return BulkImportResult(imported=imported, skipped=skipped, errors=errors[:10])
