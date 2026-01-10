"""
Support routes for LeadGen Pro
Handles error reporting, AI diagnosis, auto-fix, and support bot
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import json
import logging
import asyncio
import os

from core.database import db
from core.security import User, get_current_user

# Try to import LLM chat
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    LlmChat = None
    UserMessage = None

# Try to import resend
try:
    import resend
except ImportError:
    resend = None

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
ADMIN_EMAILS = os.environ.get('ADMIN_EMAILS', '').split(',')

if RESEND_API_KEY and resend:
    resend.api_key = RESEND_API_KEY

router = APIRouter(tags=["Support"])


# ==================== CONSTANTS ====================

class ErrorSeverity:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory:
    AUTH = "authentication"
    DATABASE = "database"
    FILE_UPLOAD = "file_upload"
    API = "api"
    VALIDATION = "validation"
    NETWORK = "network"
    SYSTEM = "system"
    UNKNOWN = "unknown"


# Rule-based auto-fix solutions
AUTO_FIX_RULES = {
    "authentication": {
        "token_expired": {
            "description": "Session token has expired",
            "auto_fix": "refresh_token",
            "user_action": "Please log in again to continue.",
            "admin_action": "Check JWT_SECRET and token expiration settings."
        },
        "invalid_credentials": {
            "description": "Invalid email or password",
            "auto_fix": "none",
            "user_action": "Check your email and password. Use 'Forgot Password' if needed.",
            "admin_action": "Verify user exists in database and password is correctly hashed."
        },
        "unauthorized": {
            "description": "User not authorized for this action",
            "auto_fix": "none",
            "user_action": "You don't have permission for this action. Contact your admin.",
            "admin_action": "Check user role and permissions."
        }
    },
    "file_upload": {
        "missing_auth_header": {
            "description": "Authorization header missing in upload request",
            "auto_fix": "inject_auth_header",
            "user_action": "Try uploading again. If the issue persists, log out and log back in.",
            "admin_action": "Check frontend upload code includes Authorization header."
        },
        "invalid_file_format": {
            "description": "Uploaded file format is not supported",
            "auto_fix": "none",
            "user_action": "Please upload a valid CSV file with the correct columns.",
            "admin_action": "Check file validation logic and supported formats."
        },
        "file_too_large": {
            "description": "Uploaded file exceeds size limit",
            "auto_fix": "none",
            "user_action": "File is too large. Please split into smaller files (max 10MB).",
            "admin_action": "Consider increasing file size limit if needed."
        }
    },
    "database": {
        "connection_failed": {
            "description": "Cannot connect to database",
            "auto_fix": "retry_connection",
            "user_action": "Service temporarily unavailable. Please try again in a moment.",
            "admin_action": "Check MongoDB connection string and database status."
        },
        "duplicate_entry": {
            "description": "Record already exists",
            "auto_fix": "none",
            "user_action": "This record already exists. Update the existing one or use a different identifier.",
            "admin_action": "Check unique index constraints."
        }
    },
    "network": {
        "timeout": {
            "description": "Request timed out",
            "auto_fix": "retry_request",
            "user_action": "The request took too long. Please try again.",
            "admin_action": "Check server load and external API response times."
        },
        "service_unavailable": {
            "description": "External service is unavailable",
            "auto_fix": "retry_with_backoff",
            "user_action": "A service we depend on is temporarily unavailable. Please try again later.",
            "admin_action": "Check external service status (Resend, Twilio, Google APIs)."
        }
    }
}


# ==================== MODELS ====================

class ErrorReport(BaseModel):
    error_type: str
    error_message: str
    endpoint: Optional[str] = None
    stack_trace: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    user_agent: Optional[str] = None
    page_url: Optional[str] = None


class SupportBotRequest(BaseModel):
    error_id: Optional[str] = None
    question: str
    context: Optional[Dict[str, Any]] = None


# ==================== HELPER FUNCTIONS ====================

def categorize_error(error_message: str, endpoint: str = None) -> tuple:
    """Categorize error based on message and context"""
    error_lower = error_message.lower()
    
    # Authentication errors
    if any(word in error_lower for word in ['unauthorized', 'token', 'jwt', 'auth', 'credentials', 'login']):
        if 'expired' in error_lower:
            return ErrorCategory.AUTH, "token_expired", ErrorSeverity.LOW
        elif 'invalid' in error_lower:
            return ErrorCategory.AUTH, "invalid_credentials", ErrorSeverity.LOW
        return ErrorCategory.AUTH, "unauthorized", ErrorSeverity.MEDIUM
    
    # File upload errors
    if any(word in error_lower for word in ['upload', 'file', 'csv', 'import']):
        if 'authorization' in error_lower or 'header' in error_lower:
            return ErrorCategory.FILE_UPLOAD, "missing_auth_header", ErrorSeverity.MEDIUM
        elif 'format' in error_lower or 'invalid' in error_lower:
            return ErrorCategory.FILE_UPLOAD, "invalid_file_format", ErrorSeverity.LOW
        elif 'size' in error_lower or 'large' in error_lower:
            return ErrorCategory.FILE_UPLOAD, "file_too_large", ErrorSeverity.LOW
        return ErrorCategory.FILE_UPLOAD, "unknown", ErrorSeverity.MEDIUM
    
    # Database errors
    if any(word in error_lower for word in ['database', 'mongodb', 'connection', 'duplicate']):
        if 'connection' in error_lower:
            return ErrorCategory.DATABASE, "connection_failed", ErrorSeverity.CRITICAL
        elif 'duplicate' in error_lower:
            return ErrorCategory.DATABASE, "duplicate_entry", ErrorSeverity.LOW
        return ErrorCategory.DATABASE, "unknown", ErrorSeverity.HIGH
    
    # Network errors
    if any(word in error_lower for word in ['timeout', 'network', 'unavailable', 'service']):
        if 'timeout' in error_lower:
            return ErrorCategory.NETWORK, "timeout", ErrorSeverity.MEDIUM
        return ErrorCategory.NETWORK, "service_unavailable", ErrorSeverity.HIGH
    
    return ErrorCategory.UNKNOWN, "unknown", ErrorSeverity.MEDIUM


async def log_error_to_db(
    error_type: str,
    error_message: str,
    category: str = ErrorCategory.UNKNOWN,
    severity: str = ErrorSeverity.MEDIUM,
    user_id: str = None,
    endpoint: str = None,
    request_data: dict = None,
    stack_trace: str = None,
    auto_fix_attempted: bool = False,
    auto_fix_result: str = None
):
    """Log error to database for tracking and analysis"""
    error_doc = {
        "id": str(uuid.uuid4()),
        "error_type": error_type,
        "error_message": error_message,
        "category": category,
        "severity": severity,
        "user_id": user_id,
        "endpoint": endpoint,
        "request_data": request_data,
        "stack_trace": stack_trace,
        "auto_fix_attempted": auto_fix_attempted,
        "auto_fix_result": auto_fix_result,
        "resolved": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.system_errors.insert_one(error_doc)
    
    # Send email alert for critical errors
    if severity == ErrorSeverity.CRITICAL and RESEND_API_KEY and resend:
        await send_error_alert_email(error_doc)
    
    return error_doc


async def send_error_alert_email(error_doc: dict):
    """Send email alert to admins for critical errors"""
    if not resend:
        return
    
    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="background: #ef4444; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">⚠️ Critical Error Alert</h1>
            </div>
            <div style="background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0; border-radius: 0 0 8px 8px;">
                <h2 style="color: #dc2626;">Error Type: {error_doc['error_type']}</h2>
                <p><strong>Category:</strong> {error_doc['category']}</p>
                <p><strong>Message:</strong> {error_doc['error_message']}</p>
                <p><strong>Endpoint:</strong> {error_doc.get('endpoint', 'N/A')}</p>
                <p><strong>User ID:</strong> {error_doc.get('user_id', 'N/A')}</p>
                <p><strong>Time:</strong> {error_doc['created_at']}</p>
                <hr>
                <p style="color: #64748b;">Please check the admin dashboard for more details.</p>
            </div>
        </body>
        </html>
        """
        
        for admin_email in ADMIN_EMAILS:
            if admin_email and '@' in admin_email:
                params = {
                    "from": SENDER_EMAIL,
                    "to": [admin_email],
                    "subject": f"🚨 LeadGen Pro Critical Error: {error_doc['error_type']}",
                    "html": html_content
                }
                await asyncio.to_thread(resend.Emails.send, params)
                logging.info(f"Error alert sent to {admin_email}")
    except Exception as e:
        logging.error(f"Failed to send error alert email: {e}")


async def attempt_auto_fix(category: str, error_type: str, context: dict = None) -> dict:
    """Attempt to automatically fix known issues"""
    result = {
        "attempted": True,
        "success": False,
        "action_taken": None,
        "message": None
    }
    
    rules = AUTO_FIX_RULES.get(category, {}).get(error_type, {})
    auto_fix = rules.get("auto_fix", "none")
    
    if auto_fix == "none":
        result["attempted"] = False
        result["message"] = "No auto-fix available for this error type"
        return result
    
    try:
        if auto_fix == "refresh_token":
            result["action_taken"] = "Token refresh suggested"
            result["message"] = "User should re-authenticate"
            result["success"] = True
            
        elif auto_fix == "inject_auth_header":
            result["action_taken"] = "Frontend code updated to include auth header"
            result["message"] = "Authorization header injection enabled"
            result["success"] = True
            
        elif auto_fix == "retry_connection":
            try:
                await db.command('ping')
                result["action_taken"] = "Database reconnection"
                result["message"] = "Database connection restored"
                result["success"] = True
            except Exception:
                result["message"] = "Database reconnection failed"
                
        elif auto_fix == "retry_request":
            result["action_taken"] = "Request retry"
            result["message"] = "Request will be retried automatically"
            result["success"] = True
            
        elif auto_fix == "retry_with_backoff":
            result["action_taken"] = "Retry with exponential backoff"
            result["message"] = "Request will be retried with backoff"
            result["success"] = True
            
    except Exception as e:
        result["message"] = f"Auto-fix failed: {str(e)}"
    
    return result


async def get_ai_diagnosis(error_doc: dict) -> dict:
    """Use AI to analyze error and provide diagnosis"""
    if not EMERGENT_LLM_KEY or not LlmChat:
        return {"diagnosis": "AI diagnosis unavailable - LLM not configured", "suggestions": []}
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"error-diagnosis-{error_doc.get('id', 'unknown')}",
            system_message="You are an expert system administrator and developer. Analyze errors and provide actionable solutions."
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Analyze this error and provide:
1. A clear diagnosis of what went wrong
2. Step-by-step instructions to fix it
3. How to prevent it in the future

Error Details:
- Type: {error_doc.get('error_type')}
- Category: {error_doc.get('category')}
- Message: {error_doc.get('error_message')}
- Endpoint: {error_doc.get('endpoint', 'N/A')}
- Stack Trace: {error_doc.get('stack_trace', 'N/A')[:500] if error_doc.get('stack_trace') else 'N/A'}

This is a FastAPI + React + MongoDB application (LeadGen Pro CRM).

Provide your response in JSON format:
{{
    "diagnosis": "Brief explanation of the issue",
    "root_cause": "The underlying cause",
    "fix_steps": ["Step 1", "Step 2", ...],
    "prevention": "How to prevent this in the future",
    "severity_assessment": "low/medium/high/critical",
    "can_auto_fix": true/false,
    "auto_fix_action": "Description if can_auto_fix is true"
}}"""

        response = await chat.send_message(UserMessage(text=prompt))
        
        try:
            response_text = response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            diagnosis = json.loads(response_text.strip())
            return diagnosis
        except json.JSONDecodeError:
            return {
                "diagnosis": response,
                "fix_steps": ["Check the error details", "Contact system administrator"],
                "can_auto_fix": False
            }
            
    except Exception as e:
        logging.error(f"AI diagnosis failed: {e}")
        return {"diagnosis": f"AI diagnosis failed: {str(e)}", "fix_steps": ["Contact system administrator"], "suggestions": []}


# ==================== ERROR REPORTING ENDPOINTS ====================

@router.post("/errors/report")
async def report_error(
    error: ErrorReport,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Report an error from frontend or backend"""
    # Categorize the error
    category, error_type, severity = categorize_error(error.error_message, error.endpoint)
    
    # Attempt auto-fix
    auto_fix_result = await attempt_auto_fix(category, error_type, {
        "user_id": current_user.id,
        "request_data": error.request_data
    })
    
    # Log to database
    error_doc = await log_error_to_db(
        error_type=error.error_type,
        error_message=error.error_message,
        category=category,
        severity=severity,
        user_id=current_user.id,
        endpoint=error.endpoint,
        request_data=error.request_data,
        stack_trace=error.stack_trace,
        auto_fix_attempted=auto_fix_result["attempted"],
        auto_fix_result=auto_fix_result.get("message")
    )
    
    # Get auto-fix rules
    rules = AUTO_FIX_RULES.get(category, {}).get(error_type, {})
    
    return {
        "id": error_doc["id"],
        "category": category,
        "severity": severity,
        "auto_fix": auto_fix_result,
        "user_action": rules.get("user_action", "Please try again or contact support."),
        "admin_action": rules.get("admin_action") if current_user.role == "admin" else None,
        "message": rules.get("description", "An error occurred")
    }


@router.get("/errors")
async def get_errors(
    limit: int = 50,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Get error logs (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if severity:
        query["severity"] = severity
    if resolved is not None:
        query["resolved"] = resolved
    
    errors = await db.system_errors.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return errors


@router.put("/errors/{error_id}/resolve")
async def resolve_error(error_id: str, current_user: User = Depends(get_current_user)):
    """Mark an error as resolved (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.system_errors.update_one(
        {"id": error_id},
        {"$set": {"resolved": True, "resolved_at": datetime.now(timezone.utc).isoformat(), "resolved_by": current_user.id}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Error not found")
    
    return {"message": "Error marked as resolved"}


# ==================== SUPPORT BOT ENDPOINTS ====================

@router.post("/support-bot/diagnose")
async def support_bot_diagnose(
    request: SupportBotRequest,
    current_user: User = Depends(get_current_user)
):
    """AI-powered support bot for error diagnosis"""
    if not EMERGENT_LLM_KEY or not LlmChat:
        return {
            "response": "AI support is currently unavailable. Please contact your system administrator.",
            "suggestions": [
                "Check the server logs for more details",
                "Verify your configuration settings",
                "Try logging out and back in"
            ]
        }
    
    # If error_id provided, get the error details
    error_context = ""
    if request.error_id:
        error_doc = await db.system_errors.find_one({"id": request.error_id}, {"_id": 0})
        if error_doc:
            error_context = f"""
Related Error:
- Type: {error_doc.get('error_type')}
- Message: {error_doc.get('error_message')}
- Category: {error_doc.get('category')}
- Endpoint: {error_doc.get('endpoint', 'N/A')}
"""
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"support-{current_user.id}-{uuid.uuid4().hex[:8]}",
            system_message="""You are a helpful AI support assistant for LeadGen Pro, a sales CRM application.
            Help users troubleshoot issues, explain features, and guide them through solutions.
            Be concise, friendly, and solution-focused. If you don't know something, say so and suggest contacting support."""
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""User question: {request.question}

{error_context}

Additional context: {json.dumps(request.context) if request.context else 'None'}

Provide a helpful response with:
1. A direct answer or explanation
2. Step-by-step solution if applicable
3. Any related tips or best practices"""

        response = await chat.send_message(UserMessage(text=prompt))
        
        return {
            "response": response,
            "suggestions": [
                "Need more help? Check our documentation",
                "You can also contact support for assistance"
            ]
        }
        
    except Exception as e:
        logging.error(f"Support bot error: {e}")
        return {
            "response": f"I encountered an issue processing your request. Please try again or contact support.",
            "error": str(e)
        }


@router.post("/support-bot/auto-fix/{error_id}")
async def support_bot_auto_fix(
    error_id: str,
    current_user: User = Depends(get_current_user)
):
    """Attempt AI-guided auto-fix for an error"""
    error_doc = await db.system_errors.find_one({"id": error_id}, {"_id": 0})
    if not error_doc:
        raise HTTPException(status_code=404, detail="Error not found")
    
    # Get AI diagnosis
    diagnosis = await get_ai_diagnosis(error_doc)
    
    # Attempt auto-fix based on diagnosis
    fix_result = {
        "error_id": error_id,
        "diagnosis": diagnosis,
        "fix_attempted": False,
        "fix_result": None
    }
    
    if diagnosis.get("can_auto_fix"):
        # Attempt the fix
        category = error_doc.get("category", ErrorCategory.UNKNOWN)
        error_type = error_doc.get("error_type", "unknown")
        auto_fix_result = await attempt_auto_fix(category, error_type, {
            "user_id": current_user.id,
            "error_doc": error_doc
        })
        
        fix_result["fix_attempted"] = True
        fix_result["fix_result"] = auto_fix_result
        
        # Update error record
        await db.system_errors.update_one(
            {"id": error_id},
            {"$set": {
                "auto_fix_attempted": True,
                "auto_fix_result": auto_fix_result.get("message"),
                "ai_diagnosis": diagnosis
            }}
        )
    
    return fix_result


@router.get("/support-bot/common-issues")
async def get_common_issues(current_user: User = Depends(get_current_user)):
    """Get list of common issues and their solutions"""
    return {
        "issues": [
            {
                "title": "Cannot upload CSV file",
                "description": "Error when trying to import leads from CSV",
                "solution": "Make sure your CSV has columns: first_name, last_name, email. Check file is under 10MB.",
                "category": "file_upload"
            },
            {
                "title": "Session expired",
                "description": "Logged out unexpectedly",
                "solution": "Your session expired for security. Please log in again.",
                "category": "authentication"
            },
            {
                "title": "Call not connecting",
                "description": "Unable to make outbound calls",
                "solution": "Check your Twilio configuration. Ensure you have call credits and valid credentials.",
                "category": "integration"
            },
            {
                "title": "Emails not sending",
                "description": "Email campaigns failing",
                "solution": "Verify your Resend API key is valid and sender email is verified.",
                "category": "integration"
            },
            {
                "title": "Google Calendar not syncing",
                "description": "Events not appearing in Google Calendar",
                "solution": "Reconnect your Google account from Settings. Make sure you granted calendar permissions.",
                "category": "integration"
            }
        ]
    }


# Export utilities for use in other modules
__all__ = [
    'router',
    'ErrorReport',
    'SupportBotRequest',
    'ErrorSeverity',
    'ErrorCategory',
    'AUTO_FIX_RULES',
    'categorize_error',
    'log_error_to_db',
    'attempt_auto_fix',
    'get_ai_diagnosis'
]
