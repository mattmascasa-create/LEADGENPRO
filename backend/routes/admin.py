"""
Admin Routes - Dashboard, Employee Management, Goals, Lead Distribution
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import uuid

from models.schemas import User, DailyGoal, DailyGoalCreate
from services.database import db
from services.auth import get_current_user, get_admin_user, is_admin_user

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard/stats")
async def admin_dashboard_stats(current_user: User = Depends(get_admin_user)):
    """Get admin dashboard statistics - full company overview"""
    employees = await db.users.find({"role": {"$in": ["employee", "manager"]}}, {"_id": 0, "password": 0}).to_list(1000)
    
    total_leads = await db.leads.count_documents({})
    total_calls = await db.call_logs.count_documents({})
    total_meetings = await db.appointments.count_documents({})
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_start = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)
    
    calls_today = await db.call_logs.count_documents({
        "created_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    meetings_today = await db.appointments.count_documents({
        "scheduled_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
    })
    
    pipeline_stages = {}
    for stage in ["prospecting", "qualified", "proposal", "negotiation", "closed"]:
        count = await db.leads.count_documents({"stage": stage})
        pipeline_stages[stage] = count
    
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


@router.get("/employees/performance")
async def get_employees_performance(current_user: User = Depends(get_admin_user)):
    """Get performance metrics for all employees (Admin only)"""
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
        
        calls_today = await db.call_logs.count_documents({
            "agent_id": emp_id,
            "created_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
        })
        calls_total = await db.call_logs.count_documents({"agent_id": emp_id})
        
        meetings_today = await db.appointments.count_documents({
            "employee_id": emp_id,
            "scheduled_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}
        })
        meetings_total = await db.appointments.count_documents({"employee_id": emp_id})
        
        leads_assigned = await db.leads.count_documents({"assigned_to": emp_id})
        leads_converted = await db.leads.count_documents({"assigned_to": emp_id, "stage": "closed"})
        
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
    
    performance_data.sort(key=lambda x: x['calls_today'], reverse=True)
    
    return performance_data


@router.post("/daily-goals")
async def set_daily_goals(goal_data: DailyGoalCreate, current_user: User = Depends(get_admin_user)):
    """Set daily goals for an employee (Admin only)"""
    employee = await db.users.find_one({"id": goal_data.employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
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
    
    await db.daily_goals.update_one(
        {"employee_id": goal_data.employee_id, "date": goal_data.date},
        {"$set": doc},
        upsert=True
    )
    
    return {"success": True, "message": "Daily goals set successfully", "goal": goal}


@router.get("/daily-goals/{employee_id}")
async def get_employee_daily_goals(
    employee_id: str,
    date: Optional[str] = None,
    current_user: User = Depends(get_admin_user)
):
    """Get daily goals for an employee (Admin only)"""
    query = {"employee_id": employee_id}
    if date:
        query["date"] = date
    
    goals = await db.daily_goals.find(query, {"_id": 0}).sort("date", -1).to_list(30)
    return goals


@router.post("/distribute-leads-roundrobin")
async def distribute_leads_roundrobin(
    lead_ids: Optional[List[str]] = None,
    current_user: User = Depends(get_admin_user)
):
    """Distribute leads to employees using round-robin (Admin only)"""
    employees = await db.users.find(
        {"role": {"$in": ["employee", "manager"]}}, 
        {"_id": 0}
    ).to_list(1000)
    
    if not employees:
        raise HTTPException(status_code=400, detail="No employees found")
    
    if lead_ids:
        query = {"id": {"$in": lead_ids}, "assigned_to": None}
    else:
        query = {"assigned_to": None}
    
    leads = await db.leads.find(query, {"_id": 0}).to_list(10000)
    
    if not leads:
        raise HTTPException(status_code=404, detail="No unassigned leads found")
    
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


# User Management endpoints
@router.get("/users")
async def get_all_users(current_user: User = Depends(get_admin_user)):
    """Get all users (Admin only)"""
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return users


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "employee"
    department: Optional[str] = None
    company: Optional[str] = None


@router.post("/users")
async def create_user(user_data: CreateUserRequest, current_user: User = Depends(get_admin_user)):
    """Create a new user (Admin only)"""
    from services.auth import get_password_hash
    
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        department=user_data.department,
        company=user_data.company,
        onboarding_completed=True  # Admin-created users skip onboarding
    )
    
    doc = user.model_dump()
    doc['password'] = get_password_hash(user_data.password)
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    
    return {"success": True, "message": "User created successfully", "user": user}


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    department: Optional[str] = None,
    current_user: User = Depends(get_admin_user)
):
    """Update a user (Admin only)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {}
    if full_name:
        update_data["full_name"] = full_name
    if role:
        update_data["role"] = role
    if department:
        update_data["department"] = department
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return updated_user


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_admin_user)):
    """Delete a user (Admin only)"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted"}
