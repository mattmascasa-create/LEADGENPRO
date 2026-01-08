"""
Integrations Routes - CRM Integrations (HubSpot, Salesforce, etc.)
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
import uuid

from models.schemas import User
from services.database import db
from services.auth import get_current_user

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class CRMIntegration(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider: str
    status: str = "disconnected"
    api_key: Optional[str] = None
    instance_url: Optional[str] = None
    last_sync: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.get("/crm")
async def get_crm_integrations(current_user: User = Depends(get_current_user)):
    """Get all CRM integrations for the current user"""
    integrations = await db.crm_integrations.find(
        {"user_id": current_user.id},
        {"_id": 0}
    ).to_list(100)
    return integrations


@router.post("/crm")
async def create_crm_integration(
    provider: str,
    api_key: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Create a new CRM integration (placeholder for future implementation)"""
    existing = await db.crm_integrations.find_one({
        "user_id": current_user.id,
        "provider": provider
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Integration already exists")
    
    integration = CRMIntegration(
        user_id=current_user.id,
        provider=provider,
        status="pending",
        api_key=api_key
    )
    
    doc = integration.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.crm_integrations.insert_one(doc)
    
    return {
        "success": True,
        "message": f"{provider} integration created. Full integration coming soon!",
        "integration": integration
    }


@router.delete("/crm/{provider}")
async def delete_crm_integration(provider: str, current_user: User = Depends(get_current_user)):
    """Delete a CRM integration"""
    result = await db.crm_integrations.delete_one({
        "user_id": current_user.id,
        "provider": provider
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {"success": True, "message": f"{provider} integration disconnected"}


@router.get("/crm/{provider}/status")
async def get_crm_integration_status(provider: str, current_user: User = Depends(get_current_user)):
    """Get status of a specific CRM integration"""
    integration = await db.crm_integrations.find_one(
        {"user_id": current_user.id, "provider": provider},
        {"_id": 0}
    )
    
    if not integration:
        return {"status": "not_connected", "provider": provider}
    
    return integration


# Webhook endpoint for CRM callbacks
@router.post("/crm/{provider}/webhook")
async def crm_webhook(provider: str, payload: dict):
    """Receive webhooks from CRM providers"""
    # Log the webhook for debugging
    await db.webhook_logs.insert_one({
        "provider": provider,
        "payload": payload,
        "received_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"received": True}
