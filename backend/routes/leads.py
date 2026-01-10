"""
Lead routes for LeadGen Pro
Handles CRUD operations, bulk imports, assignments, and web scraping
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import csv
import io
import re
import logging
import aiohttp
from bs4 import BeautifulSoup

from core.database import db
from core.security import User, get_current_user, is_admin_user, ADMIN_EMAILS

router = APIRouter(prefix="/leads", tags=["Leads"])


# ==================== MODELS ====================

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


class Activity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    description: str
    lead_id: Optional[str] = None
    user_id: str
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BulkImportResult(BaseModel):
    success: int
    failed: int
    errors: List[str] = []


class BulkAssignRequest(BaseModel):
    lead_ids: List[str]
    user_id: str


class BulkSequenceRequest(BaseModel):
    lead_ids: List[str]
    sequence_id: str


class BulkOperationResult(BaseModel):
    success: int
    failed: int
    message: str


class ScrapeRequest(BaseModel):
    url: str
    selectors: Optional[Dict[str, str]] = None


class ScrapedContact(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

async def calculate_lead_score(lead_data: dict) -> int:
    """Calculate lead score based on various factors"""
    score = 0
    
    # Company domain score
    email = lead_data.get('email', '')
    if '@' in email:
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


async def generate_ai_insight(lead_data: dict) -> str:
    """Generate AI insights for a lead - imports from main server module"""
    try:
        # Import from server module which has the LLM integration
        import server
        return await server.generate_ai_insight(lead_data)
    except Exception as e:
        logging.error(f"AI insight generation failed: {e}")
        return "AI insights will be generated shortly."


# ==================== CRUD ENDPOINTS ====================

@router.get("", response_model=List[Lead])
async def get_leads(stage: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get all leads with optional stage filter"""
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


@router.post("", response_model=Lead)
async def create_lead(lead_data: LeadCreate, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    """Create a new lead"""
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
    async def gen_insights():
        try:
            insights = await generate_ai_insight(doc)
            await db.leads.update_one(
                {"id": lead.id},
                {"$set": {"ai_insights": insights}}
            )
        except Exception as e:
            logging.error(f"Failed to generate AI insights: {e}")
    
    background_tasks.add_task(gen_insights)
    
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


@router.get("/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific lead by ID"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return Lead(**lead)


@router.put("/{lead_id}", response_model=Lead)
async def update_lead(lead_id: str, lead_data: LeadCreate, current_user: User = Depends(get_current_user)):
    """Update a lead"""
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


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Delete a lead"""
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted successfully"}


@router.post("/{lead_id}/stage")
async def update_lead_stage(lead_id: str, stage: str, current_user: User = Depends(get_current_user)):
    """Update the stage of a lead"""
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


# ==================== BULK OPERATIONS ====================

@router.post("/bulk-import", response_model=BulkImportResult)
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


@router.post("/bulk-assign", response_model=BulkOperationResult)
async def bulk_assign_leads(request: BulkAssignRequest, current_user: User = Depends(get_current_user)):
    """Assign multiple leads to a user"""
    # Verify target user exists
    target_user = await db.users.find_one({"id": request.user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    success_count = 0
    for lead_id in request.lead_ids:
        result = await db.leads.update_one(
            {"id": lead_id},
            {"$set": {
                "assigned_to": request.user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        if result.modified_count > 0:
            success_count += 1
            
            # Log activity
            await db.activities.insert_one({
                "id": str(uuid.uuid4()),
                "type": "lead_assigned",
                "description": f"Lead assigned to {target_user.get('full_name', 'user')}",
                "user_id": current_user.id,
                "lead_id": lead_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    return BulkOperationResult(
        success=success_count,
        failed=len(request.lead_ids) - success_count,
        message=f"Successfully assigned {success_count} leads to {target_user.get('full_name', 'user')}"
    )


@router.post("/bulk-sequence", response_model=BulkOperationResult)
async def bulk_add_to_sequence(request: BulkSequenceRequest, current_user: User = Depends(get_current_user)):
    """Add multiple leads to an email sequence"""
    # Verify sequence exists
    sequence = await db.sequences.find_one({"id": request.sequence_id}, {"_id": 0})
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    success_count = 0
    for lead_id in request.lead_ids:
        # Check if lead is already in sequence
        existing = await db.sequence_enrollments.find_one({
            "lead_id": lead_id,
            "sequence_id": request.sequence_id
        })
        
        if not existing:
            enrollment = {
                "id": str(uuid.uuid4()),
                "lead_id": lead_id,
                "sequence_id": request.sequence_id,
                "current_step": 0,
                "status": "active",
                "enrolled_by": current_user.id,
                "enrolled_at": datetime.now(timezone.utc).isoformat()
            }
            await db.sequence_enrollments.insert_one(enrollment)
            success_count += 1
            
            # Log activity
            await db.activities.insert_one({
                "id": str(uuid.uuid4()),
                "type": "added_to_sequence",
                "description": f"Added to sequence: {sequence.get('name', 'Unknown')}",
                "user_id": current_user.id,
                "lead_id": lead_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    return BulkOperationResult(
        success=success_count,
        failed=len(request.lead_ids) - success_count,
        message=f"Successfully added {success_count} leads to {sequence.get('name', 'sequence')}"
    )


# ==================== WEB SCRAPING ====================

@router.post("/scrape")
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


# Export models and helpers for use in other modules
__all__ = [
    'router',
    'Lead',
    'LeadCreate',
    'Activity',
    'BulkImportResult',
    'BulkAssignRequest',
    'BulkSequenceRequest',
    'BulkOperationResult',
    'ScrapeRequest',
    'ScrapedContact',
    'calculate_lead_score'
]
