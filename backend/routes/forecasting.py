"""
Forecasting routes for LeadGen Pro
Handles pipeline forecasting and AI-powered deal analysis
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import os
import logging

from core.database import db
from core.security import User, get_current_user

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

router = APIRouter(tags=["Forecasting"])


# ==================== MODELS ====================

class DealForecast(BaseModel):
    lead_id: str
    lead_name: str
    company: Optional[str]
    deal_value: float
    stage: str
    probability: int
    weighted_value: float
    last_contacted: Optional[str]


# ==================== PIPELINE FORECASTING ====================

@router.get("/forecasting/pipeline")
async def get_pipeline_forecast(current_user: User = Depends(get_current_user)):
    """Get AI-powered pipeline forecast"""
    # Get all active leads with deal values
    leads = await db.leads.find(
        {"stage": {"$nin": ["lost", "closed"]}},
        {"_id": 0}
    ).to_list(1000)
    
    # Calculate stage-based probabilities
    stage_probabilities = {
        "new": 10,
        "contacted": 20,
        "qualified": 40,
        "proposal": 60,
        "negotiation": 80,
        "won": 100,
        "lost": 0
    }
    
    forecasts = []
    total_pipeline = 0
    weighted_pipeline = 0
    
    for lead in leads:
        deal_value = lead.get("deal_value", 0) or 0
        stage = lead.get("stage", "new")
        probability = stage_probabilities.get(stage, 20)
        
        # Adjust probability based on activity
        last_contacted = lead.get("last_contacted")
        if last_contacted:
            try:
                days_since_contact = (datetime.now(timezone.utc) - datetime.fromisoformat(last_contacted.replace('Z', '+00:00'))).days
                if days_since_contact > 14:
                    probability = max(5, probability - 15)
                elif days_since_contact < 3:
                    probability = min(95, probability + 10)
            except Exception:
                pass
        
        weighted_value = deal_value * (probability / 100)
        total_pipeline += deal_value
        weighted_pipeline += weighted_value
        
        forecasts.append({
            "lead_id": lead["id"],
            "lead_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            "company": lead.get("company"),
            "deal_value": deal_value,
            "stage": stage,
            "probability": probability,
            "weighted_value": weighted_value,
            "last_contacted": last_contacted
        })
    
    # Sort by weighted value
    forecasts.sort(key=lambda x: x["weighted_value"], reverse=True)
    
    # Calculate monthly forecast
    monthly_forecast = weighted_pipeline * 0.3  # Assume 30% close in current month
    quarterly_forecast = weighted_pipeline * 0.7  # 70% close in quarter
    
    # Stage distribution
    stage_distribution = {}
    for f in forecasts:
        stage = f["stage"]
        if stage not in stage_distribution:
            stage_distribution[stage] = {"count": 0, "value": 0, "weighted": 0}
        stage_distribution[stage]["count"] += 1
        stage_distribution[stage]["value"] += f["deal_value"]
        stage_distribution[stage]["weighted"] += f["weighted_value"]
    
    return {
        "summary": {
            "total_pipeline": total_pipeline,
            "weighted_pipeline": round(weighted_pipeline, 2),
            "monthly_forecast": round(monthly_forecast, 2),
            "quarterly_forecast": round(quarterly_forecast, 2),
            "total_deals": len(forecasts),
            "avg_deal_size": round(total_pipeline / len(forecasts), 2) if forecasts else 0,
            "avg_probability": round(sum(f["probability"] for f in forecasts) / len(forecasts), 1) if forecasts else 0
        },
        "stage_distribution": [
            {"stage": stage, **data}
            for stage, data in stage_distribution.items()
        ],
        "top_deals": forecasts[:10],
        "at_risk_deals": [f for f in forecasts if f["probability"] < 30][:10]
    }


@router.post("/forecasting/analyze-deal/{lead_id}")
async def analyze_deal_forecast(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get AI analysis for a specific deal"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get activity history
    activities = await db.activities.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    
    # Get call history
    calls = await db.call_logs.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).to_list(10)
    
    # Get email history
    emails = await db.tracked_emails.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).to_list(10)
    
    # Calculate engagement score
    engagement_score = 0
    engagement_score += len(activities) * 5
    engagement_score += len(calls) * 10
    engagement_score += sum(1 for e in emails if e.get("opened_at")) * 15
    engagement_score += sum(1 for e in emails if e.get("clicked_at")) * 20
    engagement_score = min(100, engagement_score)
    
    # Determine confidence factors and risks
    confidence_factors = []
    risk_factors = []
    
    if engagement_score > 50:
        confidence_factors.append("High engagement level")
    if lead.get("stage") in ["proposal", "negotiation"]:
        confidence_factors.append("Advanced pipeline stage")
    if calls and any(c.get("outcome") == "connected" for c in calls):
        confidence_factors.append("Successful call connections")
    if any(e.get("replied_at") for e in emails):
        confidence_factors.append("Email replies received")
    
    last_contacted = lead.get("last_contacted")
    if last_contacted:
        try:
            days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last_contacted.replace('Z', '+00:00'))).days
            if days_since > 14:
                risk_factors.append(f"No contact in {days_since} days")
        except Exception:
            pass
    else:
        risk_factors.append("Never contacted")
    
    if engagement_score < 30:
        risk_factors.append("Low engagement score")
    if lead.get("stage") == "new":
        risk_factors.append("Still in early stage")
    
    # Calculate probability
    base_probability = {"new": 10, "contacted": 20, "qualified": 40, "proposal": 60, "negotiation": 80}.get(lead.get("stage"), 20)
    adjusted_probability = base_probability + (engagement_score - 50) * 0.3
    adjusted_probability = max(5, min(95, adjusted_probability))
    
    return {
        "lead": lead,
        "analysis": {
            "close_probability": round(adjusted_probability, 1),
            "engagement_score": engagement_score,
            "confidence_factors": confidence_factors,
            "risk_factors": risk_factors,
            "activity_count": len(activities),
            "call_count": len(calls),
            "email_count": len(emails),
            "emails_opened": sum(1 for e in emails if e.get("opened_at")),
            "recommendation": "Schedule a follow-up call" if risk_factors else "Continue current approach"
        }
    }


# Export router
__all__ = ['router', 'DealForecast']
