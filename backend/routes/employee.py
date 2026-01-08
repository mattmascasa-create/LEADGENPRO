"""
Employee Routes - Employee Dashboard, Personal Stats, My Leads
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends

from models.schemas import User
from services.database import db
from services.auth import get_current_user

router = APIRouter(prefix="/employee", tags=["Employee"])


@router.get("/dashboard")
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


@router.get("/my-leads")
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


@router.get("/my-tasks")
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


@router.get("/my-stats")
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
