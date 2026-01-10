"""
Stats and Insights routes for LeadGen Pro
Handles dashboard statistics, AI insights, and analytics
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid

from core.database import db
from core.security import User, get_current_user

router = APIRouter(tags=["Stats & Insights"])


# ==================== MODELS ====================

class Stats(BaseModel):
    total_leads: int = 0
    total_users: int = 0
    total_appointments: int = 0
    conversion_rate: float = 0.0
    avg_response_time: float = 0.0
    pipeline_value: float = 0.0


class AIInsight(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    insight_type: str  # follow_up_needed, hot_leads, performance, risk_alert, opportunity
    message: str
    confidence: float = 0.0
    action_items: List[str] = []
    lead_ids: List[str] = []
    priority: str = "medium"  # low, medium, high
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PerformanceMetrics(BaseModel):
    calls_made: int = 0
    calls_connected: int = 0
    emails_sent: int = 0
    emails_opened: int = 0
    meetings_scheduled: int = 0
    deals_closed: int = 0
    revenue_generated: float = 0.0
    avg_deal_size: float = 0.0
    conversion_rate: float = 0.0


# ==================== STATS ENDPOINTS ====================

@router.get("/stats", response_model=Stats)
async def get_stats(current_user: User = Depends(get_current_user)):
    """Get overall CRM statistics"""
    total_leads = await db.leads.count_documents({})
    total_users = await db.users.count_documents({})
    total_appointments = await db.appointments.count_documents({})
    
    # Calculate pipeline value
    pipeline = await db.leads.aggregate([
        {"$match": {"stage": {"$in": ["qualified", "proposal", "negotiation"]}}},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$deal_value", 0]}}}}
    ]).to_list(1)
    pipeline_value = pipeline[0]['total'] if pipeline else 0
    
    # Calculate conversion rate
    won_leads = await db.leads.count_documents({"stage": "won"})
    conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Calculate avg response time (hours)
    # This would normally query actual response times
    avg_response_time = 2.4
    
    return Stats(
        total_leads=total_leads,
        total_users=total_users,
        total_appointments=total_appointments,
        conversion_rate=round(conversion_rate, 1),
        avg_response_time=avg_response_time,
        pipeline_value=float(pipeline_value)
    )


@router.get("/stats/detailed")
async def get_detailed_stats(
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Get detailed statistics with time range"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()
    
    # Leads stats
    new_leads = await db.leads.count_documents({"created_at": {"$gte": cutoff_str}})
    qualified_leads = await db.leads.count_documents({
        "stage": {"$in": ["qualified", "proposal", "negotiation"]},
        "updated_at": {"$gte": cutoff_str}
    })
    won_leads = await db.leads.count_documents({
        "stage": "won",
        "updated_at": {"$gte": cutoff_str}
    })
    lost_leads = await db.leads.count_documents({
        "stage": "lost",
        "updated_at": {"$gte": cutoff_str}
    })
    
    # Activity stats
    total_calls = await db.call_logs.count_documents({"created_at": {"$gte": cutoff_str}})
    connected_calls = await db.call_logs.count_documents({
        "outcome": "connected",
        "created_at": {"$gte": cutoff_str}
    })
    
    total_emails = await db.tracked_emails.count_documents({"sent_at": {"$gte": cutoff_str}})
    opened_emails = await db.tracked_emails.count_documents({
        "opened_at": {"$ne": None},
        "sent_at": {"$gte": cutoff_str}
    })
    
    total_meetings = await db.appointments.count_documents({
        "scheduled_at": {"$gte": cutoff_str}
    })
    completed_meetings = await db.appointments.count_documents({
        "status": "completed",
        "scheduled_at": {"$gte": cutoff_str}
    })
    
    # Pipeline value
    pipeline = await db.leads.aggregate([
        {"$match": {"stage": {"$in": ["qualified", "proposal", "negotiation"]}}},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$deal_value", 0]}}}}
    ]).to_list(1)
    
    # Stage distribution
    stage_counts = {}
    stages = ["new", "contacted", "qualified", "proposal", "negotiation", "won", "lost"]
    for stage in stages:
        count = await db.leads.count_documents({"stage": stage})
        stage_counts[stage] = count
    
    return {
        "period_days": days,
        "leads": {
            "new": new_leads,
            "qualified": qualified_leads,
            "won": won_leads,
            "lost": lost_leads,
            "conversion_rate": round((won_leads / new_leads * 100) if new_leads > 0 else 0, 1)
        },
        "activities": {
            "calls_made": total_calls,
            "calls_connected": connected_calls,
            "call_connect_rate": round((connected_calls / total_calls * 100) if total_calls > 0 else 0, 1),
            "emails_sent": total_emails,
            "emails_opened": opened_emails,
            "email_open_rate": round((opened_emails / total_emails * 100) if total_emails > 0 else 0, 1),
            "meetings_scheduled": total_meetings,
            "meetings_completed": completed_meetings
        },
        "pipeline": {
            "total_value": pipeline[0]['total'] if pipeline else 0,
            "stage_distribution": stage_counts
        }
    }


@router.get("/stats/user/{user_id}")
async def get_user_stats(
    user_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Get statistics for a specific user"""
    # Only allow users to see their own stats or admins to see all
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()
    
    # User's lead stats
    assigned_leads = await db.leads.count_documents({"assigned_to": user_id})
    contacted_leads = await db.leads.count_documents({
        "assigned_to": user_id,
        "last_contacted": {"$ne": None}
    })
    
    # User's activity stats
    calls = await db.call_logs.count_documents({
        "agent_id": user_id,
        "created_at": {"$gte": cutoff_str}
    })
    emails = await db.tracked_emails.count_documents({
        "sent_by": user_id,
        "sent_at": {"$gte": cutoff_str}
    })
    meetings = await db.appointments.count_documents({
        "created_by": user_id,
        "scheduled_at": {"$gte": cutoff_str}
    })
    
    # Tasks completed
    tasks_completed = await db.tasks.count_documents({
        "assigned_to": user_id,
        "completed": True,
        "completed_at": {"$gte": cutoff_str}
    })
    
    return {
        "user_id": user_id,
        "period_days": days,
        "leads": {
            "assigned": assigned_leads,
            "contacted": contacted_leads,
            "contact_rate": round((contacted_leads / assigned_leads * 100) if assigned_leads > 0 else 0, 1)
        },
        "activities": {
            "calls": calls,
            "emails": emails,
            "meetings": meetings,
            "tasks_completed": tasks_completed
        }
    }


# ==================== AI INSIGHTS ENDPOINTS ====================

@router.get("/insights", response_model=List[AIInsight])
async def get_ai_insights(current_user: User = Depends(get_current_user)):
    """Get AI-generated insights for the user"""
    insights = []
    
    # Get leads without recent contact
    stale_leads = await db.leads.find({
        "assigned_to": current_user.id,
        "stage": {"$nin": ["won", "lost"]},
        "$or": [
            {"last_contacted": None},
            {"last_contacted": {"$lt": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()}}
        ]
    }, {"_id": 0, "id": 1}).to_list(10)
    
    if stale_leads:
        insights.append(AIInsight(
            insight_type="follow_up_needed",
            message=f"You have {len(stale_leads)} leads that haven't been contacted in 3+ days",
            confidence=0.95,
            action_items=["Schedule follow-up calls", "Send reminder emails"],
            lead_ids=[lead["id"] for lead in stale_leads],
            priority="high"
        ))
    
    # Get high-score leads not yet contacted
    hot_leads = await db.leads.find({
        "assigned_to": current_user.id,
        "score": {"$gte": 80},
        "stage": {"$in": ["new", "contacted"]}
    }, {"_id": 0, "id": 1}).limit(5).to_list(5)
    
    if hot_leads:
        insights.append(AIInsight(
            insight_type="hot_leads",
            message=f"{len(hot_leads)} high-priority leads ready for outreach",
            confidence=0.92,
            action_items=["Prioritize these contacts", "Use personalized approach"],
            lead_ids=[lead["id"] for lead in hot_leads],
            priority="high"
        ))
    
    # Check for deals at risk (no activity in 7 days on proposal/negotiation stage)
    at_risk = await db.leads.find({
        "assigned_to": current_user.id,
        "stage": {"$in": ["proposal", "negotiation"]},
        "last_contacted": {"$lt": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}
    }, {"_id": 0, "id": 1}).to_list(5)
    
    if at_risk:
        insights.append(AIInsight(
            insight_type="risk_alert",
            message=f"{len(at_risk)} deals at risk - no activity in 7+ days",
            confidence=0.85,
            action_items=["Re-engage immediately", "Schedule meeting or call"],
            lead_ids=[lead["id"] for lead in at_risk],
            priority="high"
        ))
    
    # Upcoming tasks reminder
    upcoming_tasks = await db.tasks.count_documents({
        "assigned_to": current_user.id,
        "completed": False,
        "due_date": {
            "$gte": datetime.now(timezone.utc).isoformat(),
            "$lte": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        }
    })
    
    if upcoming_tasks > 0:
        insights.append(AIInsight(
            insight_type="task_reminder",
            message=f"You have {upcoming_tasks} tasks due in the next 24 hours",
            confidence=1.0,
            action_items=["Review and complete pending tasks"],
            priority="medium"
        ))
    
    # Performance insight
    total_leads = await db.leads.count_documents({"assigned_to": current_user.id})
    won_leads = await db.leads.count_documents({"assigned_to": current_user.id, "stage": "won"})
    
    if total_leads > 10:
        conversion_rate = won_leads / total_leads * 100
        if conversion_rate > 20:
            insights.append(AIInsight(
                insight_type="performance",
                message=f"Great work! Your conversion rate ({conversion_rate:.1f}%) is above average.",
                confidence=0.88,
                action_items=["Share your approach with team", "Document winning strategies"],
                priority="low"
            ))
    
    return insights


@router.get("/insights/lead/{lead_id}")
async def get_lead_insights(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get AI insights for a specific lead"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    insights = []
    
    # Check engagement level
    activities = await db.activities.count_documents({"lead_id": lead_id})
    calls = await db.call_logs.count_documents({"lead_id": lead_id})
    emails = await db.tracked_emails.count_documents({"lead_id": lead_id})
    
    engagement_score = activities * 5 + calls * 10 + emails * 3
    
    if engagement_score < 20:
        insights.append({
            "type": "low_engagement",
            "message": "This lead has low engagement. Consider reaching out.",
            "action": "Schedule a call or send a personalized email"
        })
    elif engagement_score > 50:
        insights.append({
            "type": "high_engagement",
            "message": "This lead is highly engaged. Good candidate for closing.",
            "action": "Move to proposal stage if not already"
        })
    
    # Check last contact
    if lead.get("last_contacted"):
        last_contact = datetime.fromisoformat(lead["last_contacted"].replace('Z', '+00:00'))
        days_since = (datetime.now(timezone.utc) - last_contact).days
        
        if days_since > 7:
            insights.append({
                "type": "stale",
                "message": f"No contact in {days_since} days. Risk of losing interest.",
                "action": "Follow up immediately"
            })
    else:
        insights.append({
            "type": "never_contacted",
            "message": "This lead has never been contacted.",
            "action": "Make initial outreach"
        })
    
    # Suggest next best action based on stage
    stage_actions = {
        "new": "Qualify the lead with discovery questions",
        "contacted": "Schedule a follow-up call",
        "qualified": "Send a proposal or case study",
        "proposal": "Address objections and negotiate",
        "negotiation": "Close the deal"
    }
    
    current_stage = lead.get("stage", "new")
    if current_stage in stage_actions:
        insights.append({
            "type": "next_action",
            "message": f"Recommended next step for {current_stage} stage:",
            "action": stage_actions[current_stage]
        })
    
    return {
        "lead_id": lead_id,
        "engagement_score": engagement_score,
        "insights": insights
    }


# Export models and router
__all__ = [
    'router',
    'Stats',
    'AIInsight',
    'PerformanceMetrics'
]
