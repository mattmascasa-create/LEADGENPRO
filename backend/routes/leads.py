"""
Leads Routes - Lead Management, CRUD, Pipeline, and Distribution
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from models.schemas import Lead, LeadCreate, User, Activity
from services.database import db
from services.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/leads", tags=["Leads"])


class LeadUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    stage: Optional[str] = None
    score: Optional[int] = None
    tags: Optional[List[str]] = None
    assigned_to: Optional[str] = None


@router.get("")
async def get_leads(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all leads with optional filtering"""
    query = {}
    if status:
        query["status"] = status
    if stage:
        query["stage"] = stage
    
    leads = await db.leads.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return leads


@router.get("/my-leads")
async def get_my_leads(
    limit: int = 50,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get leads assigned to current user"""
    query = {"assigned_to": current_user.id}
    if status:
        query["status"] = status
    
    leads = await db.leads.find(query, {"_id": 0}).limit(limit).to_list(limit)
    return leads


@router.get("/pipeline")
async def get_pipeline(current_user: User = Depends(get_current_user)):
    """Get leads organized by pipeline stage"""
    pipeline = {}
    stages = ["prospecting", "qualified", "proposal", "negotiation", "closed"]
    
    for stage in stages:
        leads = await db.leads.find({"stage": stage}, {"_id": 0}).to_list(1000)
        pipeline[stage] = leads
    
    return pipeline


@router.post("")
async def create_lead(lead_data: LeadCreate, current_user: User = Depends(get_current_user)):
    """Create a new lead"""
    lead = Lead(**lead_data.model_dump(), created_by=current_user.id)
    
    doc = lead.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('last_contacted'):
        doc['last_contacted'] = doc['last_contacted'].isoformat()
    
    await db.leads.insert_one(doc)
    
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


@router.get("/{lead_id}")
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific lead by ID"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/{lead_id}")
async def update_lead(
    lead_id: str,
    update_data: LeadUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update a lead"""
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_dict})
    
    updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return updated_lead


@router.put("/{lead_id}/stage")
async def update_lead_stage(
    lead_id: str,
    stage: str = Query(...),
    current_user: User = Depends(get_current_user)
):
    """Update lead pipeline stage"""
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    valid_stages = ["prospecting", "qualified", "proposal", "negotiation", "closed"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    
    await db.leads.update_one(
        {"id": lead_id},
        {
            "$set": {
                "stage": stage,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log activity
    activity = Activity(
        type="stage_changed",
        description=f"Moved lead to {stage}",
        lead_id=lead_id,
        user_id=current_user.id,
        metadata={"new_stage": stage, "old_stage": lead.get("stage")}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return updated_lead


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Delete a lead"""
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted"}


@router.get("/{lead_id}/activities")
async def get_lead_activities(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get all activities for a lead"""
    activities = await db.activities.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return activities


@router.post("/bulk-import")
async def bulk_import_leads(
    leads: List[LeadCreate],
    current_user: User = Depends(get_current_user)
):
    """Bulk import leads"""
    created_leads = []
    for lead_data in leads:
        lead = Lead(**lead_data.model_dump(), created_by=current_user.id)
        doc = lead.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.leads.insert_one(doc)
        created_leads.append(lead)
    
    return {
        "message": f"Successfully imported {len(created_leads)} leads",
        "count": len(created_leads)
    }


@router.post("/{lead_id}/assign")
async def assign_lead(
    lead_id: str,
    employee_id: str,
    current_user: User = Depends(get_admin_user)
):
    """Assign a lead to an employee (Admin only)"""
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    employee = await db.users.find_one({"id": employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await db.leads.update_one(
        {"id": lead_id},
        {
            "$set": {
                "assigned_to": employee_id,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": f"Lead assigned to {employee.get('full_name', 'Unknown')}"}
