"""
Tasks routes for LeadGen Pro
Handles task CRUD and completion
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from core.database import db
from core.security import User, get_current_user

router = APIRouter(tags=["Tasks"])


# ==================== MODELS ====================

class Task(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    type: str  # call, email, meeting, follow_up, other
    lead_id: Optional[str] = None
    assigned_to: str
    assigned_name: Optional[str] = None
    due_date: datetime
    priority: str = "medium"  # low, medium, high
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str
    lead_id: Optional[str] = None
    assigned_to: str
    due_date: datetime
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    lead_id: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None


# ==================== TASK ENDPOINTS ====================

@router.get("/tasks", response_model=List[Task])
async def get_tasks(
    lead_id: Optional[str] = None,
    completed: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all tasks"""
    query = {}
    if current_user.role == "employee":
        query["assigned_to"] = current_user.id
    if lead_id:
        query["lead_id"] = lead_id
    if completed is not None:
        query["completed"] = completed
    
    tasks = await db.tasks.find(query, {"_id": 0}).to_list(1000)
    return [Task(**task) for task in tasks]


@router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, current_user: User = Depends(get_current_user)):
    """Create a new task"""
    # Get assigned user name
    assigned_user = await db.users.find_one({"id": task_data.assigned_to})
    
    task = Task(
        **task_data.model_dump(),
        created_by=current_user.id,
        assigned_name=assigned_user['full_name'] if assigned_user else None
    )
    doc = task.model_dump()
    doc['due_date'] = doc['due_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tasks.insert_one(doc)
    
    # Log activity
    activity = {
        "id": str(uuid.uuid4()),
        "type": "task_created",
        "description": f"Created task: {task.title}",
        "lead_id": task.lead_id,
        "user_id": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.activities.insert_one(activity)
    
    return task


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific task"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a task"""
    update_dict = {k: v for k, v in task_data.model_dump().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Convert datetime to ISO format
    if "due_date" in update_dict:
        update_dict["due_date"] = update_dict["due_date"].isoformat()
    
    # Update assigned name if assigned_to changed
    if "assigned_to" in update_dict:
        assigned_user = await db.users.find_one({"id": update_dict["assigned_to"]})
        update_dict["assigned_name"] = assigned_user['full_name'] if assigned_user else None
    
    result = await db.tasks.update_one(
        {"id": task_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task updated"}


@router.put("/tasks/{task_id}/complete")
async def complete_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Mark a task as completed"""
    result = await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Log activity
    task = await db.tasks.find_one({"id": task_id})
    activity = {
        "id": str(uuid.uuid4()),
        "type": "task_completed",
        "description": f"Completed task: {task['title']}",
        "lead_id": task.get('lead_id'),
        "user_id": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.activities.insert_one(activity)
    
    return {"message": "Task completed"}


@router.put("/tasks/{task_id}/uncomplete")
async def uncomplete_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Mark a task as not completed"""
    result = await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "completed": False,
            "completed_at": None
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task marked as incomplete"}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Delete a task"""
    result = await db.tasks.delete_one({"id": task_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted"}


# Export models and router
__all__ = ['router', 'Task', 'TaskCreate', 'TaskUpdate']
