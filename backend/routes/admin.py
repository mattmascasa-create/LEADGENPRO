"""
Admin routes for LeadGen Pro
Handles user management, system health, dashboard stats, and employee management
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from core.database import db
from core.security import User, get_current_user, get_password_hash, is_admin_user

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== MODELS ====================

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


class DailyGoals(BaseModel):
    calls_target: int = 50
    meetings_target: int = 5
    emails_target: int = 20


# ==================== USER MANAGEMENT ====================

@router.get("/users")
async def admin_get_users(current_user: User = Depends(get_current_user)):
    """Get all users (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return users


@router.post("/users")
async def admin_create_user(user_data: AdminUserCreate, current_user: User = Depends(get_current_user)):
    """Create a new user (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate role
    valid_roles = ['admin', 'manager', 'employee', 'client']
    if user_data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    # Create user
    user_id = str(uuid.uuid4())
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "password": get_password_hash(user_data.password),
        "full_name": user_data.full_name,
        "role": user_data.role,
        "department": user_data.department,
        "phone": user_data.phone,
        "company": user_data.company or "LeadGen Pro",
        "onboarding_completed": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(new_user)
    
    # Remove password from response
    del new_user["password"]
    return new_user


@router.put("/users/{user_id}")
async def admin_update_user(
    user_id: str,
    user_data: AdminUserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a user (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Build update dict with only provided fields
    update_data = {k: v for k, v in user_data.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return updated user
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return user


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Delete a user (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Don't allow deleting yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    new_password: str,
    current_user: User = Depends(get_current_user)
):
    """Reset a user's password (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    hashed = get_password_hash(new_password)
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"password": hashed, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Password reset successfully"}


# ==================== LEAD DISTRIBUTION ====================

@router.post("/distribute-leads")
async def admin_distribute_leads(
    lead_ids: List[str],
    current_user: User = Depends(get_current_user)
):
    """Distribute leads evenly among employees (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all employees
    employees = await db.users.find(
        {"role": {"$in": ["employee", "manager"]}},
        {"_id": 0}
    ).to_list(100)
    
    if not employees:
        raise HTTPException(status_code=400, detail="No employees found to assign leads")
    
    # Distribute leads round-robin
    assigned_count = 0
    for i, lead_id in enumerate(lead_ids):
        employee = employees[i % len(employees)]
        result = await db.leads.update_one(
            {"id": lead_id},
            {"$set": {
                "assigned_to": employee["id"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        if result.modified_count > 0:
            assigned_count += 1
    
    return {
        "message": f"Distributed {assigned_count} leads among {len(employees)} employees",
        "assigned": assigned_count,
        "total_employees": len(employees)
    }


@router.post("/distribute-leads-roundrobin")
async def admin_distribute_leads_roundrobin(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Distribute unassigned leads using round-robin (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    lead_ids = request.get("lead_ids", [])
    
    # Get unassigned leads if no specific IDs provided
    if not lead_ids:
        query = {"assigned_to": None}
    else:
        query = {"id": {"$in": lead_ids}, "assigned_to": None}
    
    unassigned = await db.leads.find(query, {"_id": 0}).to_list(1000)
    
    if not unassigned:
        return {"message": "No unassigned leads to distribute", "assigned": 0}
    
    # Get employees
    employees = await db.users.find(
        {"role": {"$in": ["employee", "manager"]}},
        {"_id": 0}
    ).to_list(100)
    
    if not employees:
        raise HTTPException(status_code=400, detail="No employees to assign leads to")
    
    # Round-robin distribution
    assigned_count = 0
    for i, lead in enumerate(unassigned):
        employee = employees[i % len(employees)]
        await db.leads.update_one(
            {"id": lead["id"]},
            {"$set": {
                "assigned_to": employee["id"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        assigned_count += 1
    
    return {
        "message": f"Assigned {assigned_count} leads to {len(employees)} employees",
        "assigned": assigned_count
    }


# ==================== SYSTEM HEALTH & ERRORS ====================

@router.get("/errors")
async def get_system_errors(current_user: User = Depends(get_current_user)):
    """Get system errors (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    errors = await db.system_errors.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).limit(100).to_list(100)
    
    return errors


@router.put("/errors/{error_id}/resolve")
async def resolve_error(error_id: str, current_user: User = Depends(get_current_user)):
    """Mark an error as resolved (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.system_errors.update_one(
        {"id": error_id},
        {"$set": {
            "resolved": True,
            "resolved_by": current_user.id,
            "resolved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Error not found")
    
    return {"message": "Error marked as resolved"}


@router.get("/system-health")
async def get_system_health(current_user: User = Depends(get_current_user)):
    """Get system health metrics (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Count documents in key collections
    leads_count = await db.leads.count_documents({})
    users_count = await db.users.count_documents({})
    calls_count = await db.call_logs.count_documents({})
    events_count = await db.calendar_events.count_documents({})
    
    # Check for recent errors
    recent_errors = await db.system_errors.count_documents({
        "resolved": {"$ne": True},
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}
    })
    
    return {
        "status": "healthy" if recent_errors == 0 else "degraded",
        "metrics": {
            "total_leads": leads_count,
            "total_users": users_count,
            "total_calls": calls_count,
            "total_events": events_count,
            "unresolved_errors": recent_errors
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ==================== DASHBOARD STATS ====================

@router.get("/dashboard/stats")
async def get_admin_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get admin dashboard statistics"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get counts
    total_leads = await db.leads.count_documents({})
    new_leads_today = await db.leads.count_documents({
        "created_at": {"$gte": today.isoformat()}
    })
    
    total_calls = await db.call_logs.count_documents({})
    calls_today = await db.call_logs.count_documents({
        "created_at": {"$gte": today.isoformat()}
    })
    
    total_meetings = await db.calendar_events.count_documents({"type": "meeting"})
    meetings_today = await db.calendar_events.count_documents({
        "type": "meeting",
        "start": {"$gte": today.isoformat(), "$lt": (today + timedelta(days=1)).isoformat()}
    })
    
    # Active employees
    employees = await db.users.count_documents({"role": {"$in": ["employee", "manager"]}})
    
    return {
        "leads": {"total": total_leads, "today": new_leads_today},
        "calls": {"total": total_calls, "today": calls_today},
        "meetings": {"total": total_meetings, "today": meetings_today},
        "employees": employees,
        "date": today.isoformat()
    }


# ==================== EMPLOYEE PERFORMANCE ====================

@router.get("/employees/performance")
async def get_employee_performance(current_user: User = Depends(get_current_user)):
    """Get performance metrics for all employees (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    employees = await db.users.find(
        {"role": {"$in": ["employee", "manager"]}},
        {"_id": 0, "password": 0}
    ).to_list(100)
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    performance = []
    for emp in employees:
        # Get metrics for this employee
        calls_today = await db.call_logs.count_documents({
            "agent_id": emp["id"],
            "created_at": {"$gte": today.isoformat()}
        })
        
        leads_assigned = await db.leads.count_documents({"assigned_to": emp["id"]})
        leads_converted = await db.leads.count_documents({
            "assigned_to": emp["id"],
            "stage": "closed_won"
        })
        
        meetings_scheduled = await db.calendar_events.count_documents({
            "$or": [{"created_by": emp["id"]}, {"attendees": emp["id"]}],
            "type": "meeting",
            "start": {"$gte": today.isoformat()}
        })
        
        performance.append({
            "employee": emp,
            "metrics": {
                "calls_today": calls_today,
                "leads_assigned": leads_assigned,
                "leads_converted": leads_converted,
                "conversion_rate": round(leads_converted / leads_assigned * 100, 1) if leads_assigned > 0 else 0,
                "meetings_today": meetings_scheduled
            }
        })
    
    return performance


# ==================== DAILY GOALS ====================

@router.post("/daily-goals")
async def set_daily_goals(
    employee_id: str,
    goals: DailyGoals,
    current_user: User = Depends(get_current_user)
):
    """Set daily goals for an employee (Admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    await db.daily_goals.update_one(
        {"employee_id": employee_id, "date": today},
        {"$set": {
            "employee_id": employee_id,
            "date": today,
            **goals.model_dump(),
            "set_by": current_user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"message": "Daily goals set successfully", "goals": goals.model_dump()}


@router.get("/daily-goals/{employee_id}")
async def get_daily_goals(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get daily goals for an employee"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    goals = await db.daily_goals.find_one(
        {"employee_id": employee_id, "date": today},
        {"_id": 0}
    )
    
    if not goals:
        # Return default goals
        return {
            "employee_id": employee_id,
            "date": today,
            "calls_target": 50,
            "meetings_target": 5,
            "emails_target": 20
        }
    
    return goals


# Export models
__all__ = [
    'router',
    'AdminUserCreate',
    'AdminUserUpdate',
    'DailyGoals'
]
