"""
Workflow Automation routes for LeadGen Pro
Handles automated lead nurturing workflows with triggers, conditions, and actions
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging
import asyncio
import os

from core.database import db
from core.security import User, get_current_user

# Try to import for email sending
try:
    import resend
except ImportError:
    resend = None

RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

if RESEND_API_KEY and resend:
    resend.api_key = RESEND_API_KEY

router = APIRouter(prefix="/workflows", tags=["Workflow Automation"])


# ==================== MODELS ====================

class WorkflowTrigger(BaseModel):
    type: str  # lead_created, lead_stage_changed, no_activity, email_opened, email_not_opened, form_submitted, tag_added
    conditions: Dict[str, Any] = {}  # {stage: "new", days_inactive: 3, etc.}


class WorkflowAction(BaseModel):
    type: str  # send_email, create_task, change_stage, add_tag, notify_user, wait, send_sms
    config: Dict[str, Any] = {}  # {template_id: "...", delay_hours: 24, etc.}
    delay_hours: int = 0  # Wait before executing this action


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    trigger: WorkflowTrigger
    actions: List[WorkflowAction] = []
    is_active: bool = True
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Stats
    total_enrolled: int = 0
    total_completed: int = 0
    total_converted: int = 0


class WorkflowEnrollment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    lead_id: str
    current_step: int = 0
    status: str = "active"  # active, paused, completed, exited
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_action_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exit_reason: Optional[str] = None
    actions_completed: List[Dict[str, Any]] = []


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger: WorkflowTrigger
    actions: List[WorkflowAction]


class WorkflowTemplate(BaseModel):
    id: str
    name: str
    description: str
    trigger: WorkflowTrigger
    actions: List[WorkflowAction]
    category: str  # nurturing, re-engagement, onboarding, follow-up


# ==================== WORKFLOW TEMPLATES ====================

WORKFLOW_TEMPLATES = [
    {
        "id": "welcome_sequence",
        "name": "Welcome Sequence",
        "description": "Automatically nurture new leads with a 3-email welcome series",
        "category": "onboarding",
        "trigger": {"type": "lead_created", "conditions": {}},
        "actions": [
            {"type": "send_email", "config": {"subject": "Welcome to {{company}}!", "template": "welcome_1"}, "delay_hours": 0},
            {"type": "wait", "config": {}, "delay_hours": 48},
            {"type": "send_email", "config": {"subject": "Here's how we can help", "template": "welcome_2"}, "delay_hours": 0},
            {"type": "wait", "config": {}, "delay_hours": 72},
            {"type": "send_email", "config": {"subject": "Ready to chat?", "template": "welcome_3"}, "delay_hours": 0},
            {"type": "create_task", "config": {"title": "Follow up with {{first_name}}", "type": "call"}, "delay_hours": 0}
        ]
    },
    {
        "id": "no_response_follow_up",
        "name": "No Response Follow-up",
        "description": "Re-engage leads who haven't responded in 3 days",
        "category": "re-engagement",
        "trigger": {"type": "no_activity", "conditions": {"days_inactive": 3}},
        "actions": [
            {"type": "send_email", "config": {"subject": "Just checking in, {{first_name}}", "template": "follow_up_1"}, "delay_hours": 0},
            {"type": "wait", "config": {}, "delay_hours": 48},
            {"type": "send_email", "config": {"subject": "Did you see my last email?", "template": "follow_up_2"}, "delay_hours": 0},
            {"type": "create_task", "config": {"title": "Call {{first_name}} - no response", "type": "call", "priority": "high"}, "delay_hours": 24}
        ]
    },
    {
        "id": "proposal_follow_up",
        "name": "Proposal Follow-up",
        "description": "Follow up after sending a proposal",
        "category": "follow-up",
        "trigger": {"type": "lead_stage_changed", "conditions": {"new_stage": "proposal"}},
        "actions": [
            {"type": "wait", "config": {}, "delay_hours": 24},
            {"type": "send_email", "config": {"subject": "Any questions about the proposal?", "template": "proposal_follow_up"}, "delay_hours": 0},
            {"type": "wait", "config": {}, "delay_hours": 72},
            {"type": "create_task", "config": {"title": "Follow up on proposal for {{first_name}}", "type": "call", "priority": "high"}, "delay_hours": 0},
            {"type": "notify_user", "config": {"message": "Proposal follow-up needed for {{lead_name}}"}, "delay_hours": 0}
        ]
    },
    {
        "id": "stale_deal_alert",
        "name": "Stale Deal Alert",
        "description": "Alert when a deal hasn't progressed in 7 days",
        "category": "nurturing",
        "trigger": {"type": "no_activity", "conditions": {"days_inactive": 7, "stages": ["qualified", "proposal", "negotiation"]}},
        "actions": [
            {"type": "notify_user", "config": {"message": "Deal with {{lead_name}} is stale - no activity in 7 days"}, "delay_hours": 0},
            {"type": "create_task", "config": {"title": "Re-engage {{first_name}} - deal stale", "type": "call", "priority": "high"}, "delay_hours": 0},
            {"type": "add_tag", "config": {"tag": "at_risk"}, "delay_hours": 0}
        ]
    },
    {
        "id": "email_engagement",
        "name": "Email Engagement Workflow",
        "description": "Follow up when lead opens an email",
        "category": "nurturing",
        "trigger": {"type": "email_opened", "conditions": {}},
        "actions": [
            {"type": "notify_user", "config": {"message": "{{lead_name}} just opened your email!"}, "delay_hours": 0},
            {"type": "create_task", "config": {"title": "Strike while hot - {{first_name}} opened email", "type": "call", "priority": "high"}, "delay_hours": 0}
        ]
    }
]


# ==================== HELPER FUNCTIONS ====================

async def personalize_content(template: str, lead: dict) -> str:
    """Replace template variables with lead data"""
    replacements = {
        "{{first_name}}": lead.get("first_name", ""),
        "{{last_name}}": lead.get("last_name", ""),
        "{{full_name}}": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        "{{lead_name}}": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        "{{company}}": lead.get("company", ""),
        "{{email}}": lead.get("email", ""),
        "{{title}}": lead.get("title", ""),
    }
    
    result = template
    for var, value in replacements.items():
        result = result.replace(var, value)
    
    return result


async def execute_workflow_action(action: dict, lead: dict, enrollment: dict, workflow: dict) -> dict:
    """Execute a single workflow action"""
    action_type = action.get("type")
    config = action.get("config", {})
    result = {"success": False, "action": action_type, "message": ""}
    
    try:
        if action_type == "send_email":
            # Send email to lead
            if resend and RESEND_API_KEY:
                subject = await personalize_content(config.get("subject", ""), lead)
                body = await personalize_content(config.get("body", f"Hi {lead.get('first_name', 'there')},\n\nJust checking in..."), lead)
                
                params = {
                    "from": SENDER_EMAIL,
                    "to": [lead.get("email")],
                    "subject": subject,
                    "html": f"<div style='font-family: Arial, sans-serif;'>{body.replace(chr(10), '<br>')}</div>"
                }
                await asyncio.to_thread(resend.Emails.send, params)
                result["success"] = True
                result["message"] = f"Email sent: {subject}"
            else:
                result["message"] = "Email service not configured"
                
        elif action_type == "create_task":
            # Create a task for the lead owner
            title = await personalize_content(config.get("title", "Follow up"), lead)
            task_doc = {
                "id": str(uuid.uuid4()),
                "title": title,
                "description": f"Auto-created by workflow: {workflow.get('name')}",
                "type": config.get("type", "follow_up"),
                "lead_id": lead.get("id"),
                "assigned_to": lead.get("assigned_to"),
                "due_date": (datetime.now(timezone.utc) + timedelta(hours=config.get("due_in_hours", 24))).isoformat(),
                "priority": config.get("priority", "medium"),
                "completed": False,
                "source": "workflow",
                "workflow_id": workflow.get("id"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.tasks.insert_one(task_doc)
            result["success"] = True
            result["message"] = f"Task created: {title}"
            
        elif action_type == "change_stage":
            # Update lead stage
            new_stage = config.get("stage")
            if new_stage:
                await db.leads.update_one(
                    {"id": lead.get("id")},
                    {"$set": {"stage": new_stage, "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                result["success"] = True
                result["message"] = f"Stage changed to: {new_stage}"
                
        elif action_type == "add_tag":
            # Add tag to lead
            tag = config.get("tag")
            if tag:
                await db.leads.update_one(
                    {"id": lead.get("id")},
                    {"$addToSet": {"tags": tag}}
                )
                result["success"] = True
                result["message"] = f"Tag added: {tag}"
                
        elif action_type == "notify_user":
            # Create notification for lead owner
            message = await personalize_content(config.get("message", "Workflow notification"), lead)
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": lead.get("assigned_to"),
                "type": "workflow",
                "title": f"Workflow: {workflow.get('name')}",
                "message": message,
                "lead_id": lead.get("id"),
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notification)
            result["success"] = True
            result["message"] = f"Notification sent"
            
        elif action_type == "wait":
            # Wait action - just mark as completed
            result["success"] = True
            result["message"] = f"Wait period completed"
            
    except Exception as e:
        logging.error(f"Workflow action failed: {e}")
        result["message"] = str(e)
    
    return result


async def process_workflow_enrollment(enrollment_id: str):
    """Process next action for an enrollment"""
    enrollment = await db.workflow_enrollments.find_one({"id": enrollment_id}, {"_id": 0})
    if not enrollment or enrollment.get("status") != "active":
        return
    
    workflow = await db.workflows.find_one({"id": enrollment["workflow_id"]}, {"_id": 0})
    if not workflow or not workflow.get("is_active"):
        return
    
    lead = await db.leads.find_one({"id": enrollment["lead_id"]}, {"_id": 0})
    if not lead:
        return
    
    actions = workflow.get("actions", [])
    current_step = enrollment.get("current_step", 0)
    
    if current_step >= len(actions):
        # Workflow completed
        await db.workflow_enrollments.update_one(
            {"id": enrollment_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        await db.workflows.update_one(
            {"id": workflow["id"]},
            {"$inc": {"total_completed": 1}}
        )
        return
    
    # Execute current action
    action = actions[current_step]
    result = await execute_workflow_action(action, lead, enrollment, workflow)
    
    # Log action result
    action_log = {
        "step": current_step,
        "action": action,
        "result": result,
        "executed_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Calculate next action time
    next_action_at = None
    if current_step + 1 < len(actions):
        next_action = actions[current_step + 1]
        delay_hours = next_action.get("delay_hours", 0)
        next_action_at = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
    
    # Update enrollment
    await db.workflow_enrollments.update_one(
        {"id": enrollment_id},
        {
            "$set": {
                "current_step": current_step + 1,
                "next_action_at": next_action_at.isoformat() if next_action_at else None
            },
            "$push": {"actions_completed": action_log}
        }
    )


# ==================== WORKFLOW ENDPOINTS ====================

@router.get("/templates")
async def get_workflow_templates(current_user: User = Depends(get_current_user)):
    """Get pre-built workflow templates"""
    return {"templates": WORKFLOW_TEMPLATES}


@router.get("")
async def get_workflows(current_user: User = Depends(get_current_user)):
    """Get all workflows"""
    workflows = await db.workflows.find({}, {"_id": 0}).to_list(100)
    return workflows


@router.post("")
async def create_workflow(workflow_data: WorkflowCreate, current_user: User = Depends(get_current_user)):
    """Create a new workflow"""
    workflow = Workflow(
        name=workflow_data.name,
        description=workflow_data.description,
        trigger=workflow_data.trigger,
        actions=workflow_data.actions,
        created_by=current_user.id
    )
    
    doc = workflow.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    doc["trigger"] = doc["trigger"].model_dump() if hasattr(doc["trigger"], "model_dump") else doc["trigger"]
    doc["actions"] = [a.model_dump() if hasattr(a, "model_dump") else a for a in doc["actions"]]
    
    await db.workflows.insert_one(doc)
    return {"success": True, "workflow": doc}


@router.post("/from-template/{template_id}")
async def create_workflow_from_template(
    template_id: str,
    name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Create a workflow from a template"""
    template = next((t for t in WORKFLOW_TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    workflow = Workflow(
        name=name or template["name"],
        description=template["description"],
        trigger=WorkflowTrigger(**template["trigger"]),
        actions=[WorkflowAction(**a) for a in template["actions"]],
        created_by=current_user.id
    )
    
    doc = workflow.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    doc["trigger"] = doc["trigger"].model_dump() if hasattr(doc["trigger"], "model_dump") else doc["trigger"]
    doc["actions"] = [a.model_dump() if hasattr(a, "model_dump") else a for a in doc["actions"]]
    
    await db.workflows.insert_one(doc)
    return {"success": True, "workflow": doc}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, current_user: User = Depends(get_current_user)):
    """Get workflow details with enrollments"""
    workflow = await db.workflows.find_one({"id": workflow_id}, {"_id": 0})
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Get enrollments
    enrollments = await db.workflow_enrollments.find(
        {"workflow_id": workflow_id},
        {"_id": 0}
    ).limit(100).to_list(100)
    
    return {"workflow": workflow, "enrollments": enrollments}


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowCreate,
    current_user: User = Depends(get_current_user)
):
    """Update a workflow"""
    update_data = {
        "name": workflow_data.name,
        "description": workflow_data.description,
        "trigger": workflow_data.trigger.model_dump(),
        "actions": [a.model_dump() for a in workflow_data.actions],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.workflows.update_one(
        {"id": workflow_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {"success": True, "message": "Workflow updated"}


@router.put("/{workflow_id}/toggle")
async def toggle_workflow(workflow_id: str, current_user: User = Depends(get_current_user)):
    """Enable or disable a workflow"""
    workflow = await db.workflows.find_one({"id": workflow_id}, {"_id": 0})
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    new_status = not workflow.get("is_active", True)
    await db.workflows.update_one(
        {"id": workflow_id},
        {"$set": {"is_active": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "is_active": new_status}


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, current_user: User = Depends(get_current_user)):
    """Delete a workflow"""
    result = await db.workflows.delete_one({"id": workflow_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Also remove enrollments
    await db.workflow_enrollments.delete_many({"workflow_id": workflow_id})
    
    return {"success": True, "message": "Workflow deleted"}


# ==================== ENROLLMENT ENDPOINTS ====================

@router.post("/{workflow_id}/enroll/{lead_id}")
async def enroll_lead(
    workflow_id: str,
    lead_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Manually enroll a lead in a workflow"""
    workflow = await db.workflows.find_one({"id": workflow_id}, {"_id": 0})
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check if already enrolled
    existing = await db.workflow_enrollments.find_one({
        "workflow_id": workflow_id,
        "lead_id": lead_id,
        "status": "active"
    })
    if existing:
        return {"success": False, "message": "Lead already enrolled in this workflow"}
    
    # Create enrollment
    enrollment = WorkflowEnrollment(
        workflow_id=workflow_id,
        lead_id=lead_id,
        next_action_at=datetime.now(timezone.utc)
    )
    
    doc = enrollment.model_dump()
    doc["enrolled_at"] = doc["enrolled_at"].isoformat()
    doc["next_action_at"] = doc["next_action_at"].isoformat() if doc["next_action_at"] else None
    
    await db.workflow_enrollments.insert_one(doc)
    
    # Update workflow stats
    await db.workflows.update_one(
        {"id": workflow_id},
        {"$inc": {"total_enrolled": 1}}
    )
    
    # Process first action immediately
    background_tasks.add_task(process_workflow_enrollment, enrollment.id)
    
    return {"success": True, "enrollment_id": enrollment.id}


@router.post("/{workflow_id}/enroll-bulk")
async def enroll_leads_bulk(
    workflow_id: str,
    lead_ids: List[str],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Enroll multiple leads in a workflow"""
    workflow = await db.workflows.find_one({"id": workflow_id}, {"_id": 0})
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    enrolled = 0
    skipped = 0
    
    for lead_id in lead_ids:
        # Check if already enrolled
        existing = await db.workflow_enrollments.find_one({
            "workflow_id": workflow_id,
            "lead_id": lead_id,
            "status": "active"
        })
        if existing:
            skipped += 1
            continue
        
        # Create enrollment
        enrollment = WorkflowEnrollment(
            workflow_id=workflow_id,
            lead_id=lead_id,
            next_action_at=datetime.now(timezone.utc)
        )
        
        doc = enrollment.model_dump()
        doc["enrolled_at"] = doc["enrolled_at"].isoformat()
        doc["next_action_at"] = doc["next_action_at"].isoformat() if doc["next_action_at"] else None
        
        await db.workflow_enrollments.insert_one(doc)
        enrolled += 1
        
        # Process first action
        background_tasks.add_task(process_workflow_enrollment, enrollment.id)
    
    # Update workflow stats
    await db.workflows.update_one(
        {"id": workflow_id},
        {"$inc": {"total_enrolled": enrolled}}
    )
    
    return {"success": True, "enrolled": enrolled, "skipped": skipped}


@router.post("/enrollments/{enrollment_id}/pause")
async def pause_enrollment(enrollment_id: str, current_user: User = Depends(get_current_user)):
    """Pause an enrollment"""
    result = await db.workflow_enrollments.update_one(
        {"id": enrollment_id, "status": "active"},
        {"$set": {"status": "paused"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Active enrollment not found")
    return {"success": True}


@router.post("/enrollments/{enrollment_id}/resume")
async def resume_enrollment(
    enrollment_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Resume a paused enrollment"""
    result = await db.workflow_enrollments.update_one(
        {"id": enrollment_id, "status": "paused"},
        {"$set": {"status": "active", "next_action_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Paused enrollment not found")
    
    background_tasks.add_task(process_workflow_enrollment, enrollment_id)
    return {"success": True}


@router.delete("/enrollments/{enrollment_id}")
async def remove_enrollment(enrollment_id: str, current_user: User = Depends(get_current_user)):
    """Remove a lead from a workflow"""
    result = await db.workflow_enrollments.update_one(
        {"id": enrollment_id},
        {"$set": {"status": "exited", "exit_reason": "manually_removed"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return {"success": True}


# ==================== PROCESSING ENDPOINT ====================

@router.post("/process-pending")
async def process_pending_workflows(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Process all pending workflow actions (called by cron or manually)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Find enrollments ready to process
    pending = await db.workflow_enrollments.find({
        "status": "active",
        "next_action_at": {"$lte": now}
    }, {"_id": 0, "id": 1}).to_list(100)
    
    for enrollment in pending:
        background_tasks.add_task(process_workflow_enrollment, enrollment["id"])
    
    return {"success": True, "processing": len(pending)}


# Export
__all__ = ['router', 'Workflow', 'WorkflowAction', 'WorkflowTrigger', 'WorkflowEnrollment', 'WORKFLOW_TEMPLATES']
