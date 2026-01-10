"""
Deal Velocity routes for LeadGen Pro
Tracks how long deals spend in each stage, identifies bottlenecks, and provides pipeline analytics
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
from collections import defaultdict

from core.database import db
from core.security import User, get_current_user

router = APIRouter(prefix="/deal-velocity", tags=["Deal Velocity"])


# ==================== MODELS ====================

class StageTransition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    from_stage: Optional[str] = None
    to_stage: str
    transitioned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    transitioned_by: Optional[str] = None
    time_in_previous_stage_hours: Optional[float] = None


class VelocityMetrics(BaseModel):
    stage: str
    avg_time_hours: float
    median_time_hours: float
    min_time_hours: float
    max_time_hours: float
    deal_count: int
    bottleneck_score: float  # 0-100, higher = more of a bottleneck


class PipelineVelocity(BaseModel):
    total_deals: int
    avg_cycle_time_days: float
    stages: List[VelocityMetrics]
    bottlenecks: List[str]
    fastest_deal_days: float
    slowest_deal_days: float


# Stage order for pipeline
STAGE_ORDER = ["new", "contacted", "qualified", "proposal", "negotiation", "won", "lost"]


# ==================== HELPER FUNCTIONS ====================

async def record_stage_transition(lead_id: str, from_stage: str, to_stage: str, user_id: str = None):
    """Record a stage transition for velocity tracking"""
    # Calculate time in previous stage
    time_in_stage = None
    if from_stage:
        # Find last transition to this stage
        last_transition = await db.stage_transitions.find_one(
            {"lead_id": lead_id, "to_stage": from_stage},
            sort=[("transitioned_at", -1)]
        )
        if last_transition:
            last_time = datetime.fromisoformat(last_transition["transitioned_at"].replace('Z', '+00:00'))
            time_in_stage = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
    
    transition = StageTransition(
        lead_id=lead_id,
        from_stage=from_stage,
        to_stage=to_stage,
        transitioned_by=user_id,
        time_in_previous_stage_hours=time_in_stage
    )
    
    doc = transition.model_dump()
    doc["transitioned_at"] = doc["transitioned_at"].isoformat()
    await db.stage_transitions.insert_one(doc)
    
    return transition


def calculate_percentile(values: List[float], percentile: int) -> float:
    """Calculate percentile of a list of values"""
    if not values:
        return 0
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * percentile / 100
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_values):
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (index - lower)


# ==================== ENDPOINTS ====================

@router.get("/overview")
async def get_velocity_overview(
    days: int = 90,
    current_user: User = Depends(get_current_user)
):
    """Get pipeline velocity overview"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()
    
    # Get all transitions in period
    transitions = await db.stage_transitions.find(
        {"transitioned_at": {"$gte": cutoff_str}},
        {"_id": 0}
    ).to_list(10000)
    
    # Group by stage
    stage_times = defaultdict(list)
    for t in transitions:
        if t.get("time_in_previous_stage_hours") and t.get("from_stage"):
            stage_times[t["from_stage"]].append(t["time_in_previous_stage_hours"])
    
    # Calculate metrics per stage
    stage_metrics = []
    max_avg_time = 0
    
    for stage in STAGE_ORDER[:-2]:  # Exclude won/lost
        times = stage_times.get(stage, [])
        if times:
            avg_time = sum(times) / len(times)
            max_avg_time = max(max_avg_time, avg_time)
            stage_metrics.append({
                "stage": stage,
                "avg_time_hours": round(avg_time, 1),
                "median_time_hours": round(calculate_percentile(times, 50), 1),
                "min_time_hours": round(min(times), 1),
                "max_time_hours": round(max(times), 1),
                "deal_count": len(times),
                "bottleneck_score": 0  # Will calculate below
            })
        else:
            stage_metrics.append({
                "stage": stage,
                "avg_time_hours": 0,
                "median_time_hours": 0,
                "min_time_hours": 0,
                "max_time_hours": 0,
                "deal_count": 0,
                "bottleneck_score": 0
            })
    
    # Calculate bottleneck scores (relative to max)
    bottlenecks = []
    for metric in stage_metrics:
        if max_avg_time > 0 and metric["avg_time_hours"] > 0:
            score = (metric["avg_time_hours"] / max_avg_time) * 100
            metric["bottleneck_score"] = round(score, 1)
            if score > 70:
                bottlenecks.append(metric["stage"])
    
    # Calculate overall cycle time for won deals
    won_leads = await db.leads.find(
        {"stage": "won", "updated_at": {"$gte": cutoff_str}},
        {"_id": 0, "id": 1, "created_at": 1, "updated_at": 1}
    ).to_list(500)
    
    cycle_times = []
    for lead in won_leads:
        try:
            created = datetime.fromisoformat(lead["created_at"].replace('Z', '+00:00'))
            won_at = datetime.fromisoformat(lead["updated_at"].replace('Z', '+00:00'))
            cycle_days = (won_at - created).total_seconds() / 86400
            cycle_times.append(cycle_days)
        except Exception:
            pass
    
    avg_cycle = sum(cycle_times) / len(cycle_times) if cycle_times else 0
    
    return {
        "period_days": days,
        "total_transitions": len(transitions),
        "avg_cycle_time_days": round(avg_cycle, 1),
        "fastest_deal_days": round(min(cycle_times), 1) if cycle_times else 0,
        "slowest_deal_days": round(max(cycle_times), 1) if cycle_times else 0,
        "stages": stage_metrics,
        "bottlenecks": bottlenecks,
        "insights": [
            f"Average deal cycle: {round(avg_cycle, 1)} days" if avg_cycle else "No won deals in period",
            f"Main bottleneck: {bottlenecks[0]} stage" if bottlenecks else "No significant bottlenecks",
            f"Analyzed {len(transitions)} stage transitions"
        ]
    }


@router.get("/by-stage/{stage}")
async def get_stage_velocity(
    stage: str,
    days: int = 90,
    current_user: User = Depends(get_current_user)
):
    """Get detailed velocity metrics for a specific stage"""
    if stage not in STAGE_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {STAGE_ORDER}")
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()
    
    # Get transitions from this stage
    transitions = await db.stage_transitions.find(
        {"from_stage": stage, "transitioned_at": {"$gte": cutoff_str}, "time_in_previous_stage_hours": {"$ne": None}},
        {"_id": 0}
    ).to_list(1000)
    
    if not transitions:
        return {
            "stage": stage,
            "period_days": days,
            "message": "No transitions from this stage in the selected period"
        }
    
    times = [t["time_in_previous_stage_hours"] for t in transitions]
    
    # Distribution buckets
    buckets = {"< 24h": 0, "1-3 days": 0, "3-7 days": 0, "1-2 weeks": 0, "2+ weeks": 0}
    for time_hours in times:
        if time_hours < 24:
            buckets["< 24h"] += 1
        elif time_hours < 72:
            buckets["1-3 days"] += 1
        elif time_hours < 168:
            buckets["3-7 days"] += 1
        elif time_hours < 336:
            buckets["1-2 weeks"] += 1
        else:
            buckets["2+ weeks"] += 1
    
    # Get destination stages
    destinations = defaultdict(int)
    for t in transitions:
        destinations[t["to_stage"]] += 1
    
    return {
        "stage": stage,
        "period_days": days,
        "total_deals": len(times),
        "metrics": {
            "avg_time_hours": round(sum(times) / len(times), 1),
            "avg_time_days": round(sum(times) / len(times) / 24, 1),
            "median_time_hours": round(calculate_percentile(times, 50), 1),
            "p90_time_hours": round(calculate_percentile(times, 90), 1),
            "min_time_hours": round(min(times), 1),
            "max_time_hours": round(max(times), 1)
        },
        "time_distribution": buckets,
        "next_stages": dict(destinations),
        "conversion_to_next": round(destinations.get(STAGE_ORDER[STAGE_ORDER.index(stage) + 1], 0) / len(times) * 100, 1) if stage not in ["won", "lost"] else None
    }


@router.get("/stale-deals")
async def get_stale_deals(
    threshold_days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """Get deals that have been stale (no stage change) for too long"""
    threshold = datetime.now(timezone.utc) - timedelta(days=threshold_days)
    threshold_str = threshold.isoformat()
    
    # Get leads in active stages that haven't been updated
    stale_leads = await db.leads.find({
        "stage": {"$in": ["contacted", "qualified", "proposal", "negotiation"]},
        "$or": [
            {"last_stage_change": {"$lt": threshold_str}},
            {"last_stage_change": {"$exists": False}, "updated_at": {"$lt": threshold_str}}
        ]
    }, {"_id": 0}).to_list(100)
    
    # Calculate days stale for each
    results = []
    for lead in stale_leads:
        last_change = lead.get("last_stage_change") or lead.get("updated_at") or lead.get("created_at")
        try:
            last_dt = datetime.fromisoformat(last_change.replace('Z', '+00:00'))
            days_stale = (datetime.now(timezone.utc) - last_dt).days
            results.append({
                "lead_id": lead["id"],
                "name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                "company": lead.get("company"),
                "stage": lead.get("stage"),
                "days_stale": days_stale,
                "deal_value": lead.get("deal_value", 0),
                "assigned_to": lead.get("assigned_to"),
                "risk_level": "high" if days_stale > 14 else "medium" if days_stale > 7 else "low"
            })
        except Exception:
            pass
    
    # Sort by days stale
    results.sort(key=lambda x: x["days_stale"], reverse=True)
    
    # Calculate at-risk pipeline value
    high_risk_value = sum(r["deal_value"] or 0 for r in results if r["risk_level"] == "high")
    medium_risk_value = sum(r["deal_value"] or 0 for r in results if r["risk_level"] == "medium")
    
    return {
        "threshold_days": threshold_days,
        "total_stale": len(results),
        "at_risk_value": {
            "high": high_risk_value,
            "medium": medium_risk_value,
            "total": high_risk_value + medium_risk_value
        },
        "by_risk_level": {
            "high": len([r for r in results if r["risk_level"] == "high"]),
            "medium": len([r for r in results if r["risk_level"] == "medium"]),
            "low": len([r for r in results if r["risk_level"] == "low"])
        },
        "stale_deals": results
    }


@router.get("/lead/{lead_id}/history")
async def get_lead_velocity_history(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get stage transition history for a specific lead"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    transitions = await db.stage_transitions.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("transitioned_at", 1).to_list(100)
    
    # Calculate total time in each stage
    stage_times = {}
    for t in transitions:
        if t.get("from_stage") and t.get("time_in_previous_stage_hours"):
            stage = t["from_stage"]
            if stage not in stage_times:
                stage_times[stage] = 0
            stage_times[stage] += t["time_in_previous_stage_hours"]
    
    # Calculate total cycle time
    total_hours = sum(stage_times.values())
    
    return {
        "lead_id": lead_id,
        "lead_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        "current_stage": lead.get("stage"),
        "created_at": lead.get("created_at"),
        "total_cycle_hours": round(total_hours, 1),
        "total_cycle_days": round(total_hours / 24, 1),
        "time_by_stage": {k: round(v, 1) for k, v in stage_times.items()},
        "transitions": transitions
    }


@router.get("/comparison")
async def get_velocity_comparison(
    days: int = 90,
    current_user: User = Depends(get_current_user)
):
    """Compare velocity metrics by user/team"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()
    
    # Get won deals with cycle time
    pipeline = [
        {"$match": {"stage": "won", "updated_at": {"$gte": cutoff_str}}},
        {"$group": {
            "_id": "$assigned_to",
            "deals_won": {"$sum": 1},
            "total_value": {"$sum": {"$ifNull": ["$deal_value", 0]}}
        }}
    ]
    
    results = await db.leads.aggregate(pipeline).to_list(50)
    
    # Enrich with user details and calculate avg cycle time
    comparisons = []
    for r in results:
        user = await db.users.find_one({"id": r["_id"]}, {"_id": 0, "full_name": 1})
        
        # Get avg cycle time for this user's won deals
        user_leads = await db.leads.find({
            "assigned_to": r["_id"],
            "stage": "won",
            "updated_at": {"$gte": cutoff_str}
        }, {"_id": 0, "created_at": 1, "updated_at": 1}).to_list(100)
        
        cycle_times = []
        for lead in user_leads:
            try:
                created = datetime.fromisoformat(lead["created_at"].replace('Z', '+00:00'))
                won = datetime.fromisoformat(lead["updated_at"].replace('Z', '+00:00'))
                cycle_times.append((won - created).total_seconds() / 86400)
            except Exception:
                pass
        
        avg_cycle = sum(cycle_times) / len(cycle_times) if cycle_times else 0
        
        comparisons.append({
            "user_id": r["_id"],
            "user_name": user.get("full_name", "Unknown") if user else "Unknown",
            "deals_won": r["deals_won"],
            "total_value": r["total_value"],
            "avg_cycle_days": round(avg_cycle, 1),
            "avg_deal_value": round(r["total_value"] / r["deals_won"], 2) if r["deals_won"] > 0 else 0
        })
    
    # Sort by deals won
    comparisons.sort(key=lambda x: x["deals_won"], reverse=True)
    
    return {
        "period_days": days,
        "comparisons": comparisons
    }


@router.post("/track-transition")
async def track_stage_transition(
    lead_id: str,
    from_stage: str,
    to_stage: str,
    current_user: User = Depends(get_current_user)
):
    """Manually track a stage transition (usually called automatically on lead update)"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    transition = await record_stage_transition(lead_id, from_stage, to_stage, current_user.id)
    
    # Update lead's last stage change
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"last_stage_change": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "transition_id": transition.id}


# Export
__all__ = ['router', 'StageTransition', 'record_stage_transition', 'STAGE_ORDER']
