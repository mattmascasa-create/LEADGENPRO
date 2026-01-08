"""
LeadGen Pro - Authentication Routes
Handles user registration, login, profile, and Google OAuth
"""

from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
import httpx
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# Database connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'leadgenpro')]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 30))

# Admin emails
ADMIN_EMAILS = ['mattmascasa@gmail.com', 'monika.iordanoff@gmail.com', 'admin@test.com']

# ==================== Request Models ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "employee"
    company: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    department: Optional[str] = None

class GoogleAuthRequest(BaseModel):
    session_id: str

# ==================== Endpoints ====================

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    """Register a new user (disabled for public - admin must create users)"""
    # Check if user already exists
    existing = await db.users.find_one({"email": user_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Determine role - admins get admin role
    role = "admin" if user_data.email.lower() in [e.lower() for e in ADMIN_EMAILS] else user_data.role
    
    user = {
        "id": str(uuid.uuid4()),
        "email": user_data.email.lower(),
        "hashed_password": get_password_hash(user_data.password),
        "full_name": user_data.full_name,
        "role": role,
        "company": user_data.company,
        "onboarding_completed": False,
        "google_linked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user)
    
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    user_response = User(**{k: v for k, v in user.items() if k != "hashed_password"})
    return Token(access_token=access_token, token_type="bearer", user=user_response)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login with email and password"""
    user = await db.users.find_one({"email": credentials.email.lower()}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(credentials.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    user_response = User(**{k: v for k, v in user.items() if k != "hashed_password"})
    return Token(access_token=access_token, token_type="bearer", user=user_response)


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.put("/profile")
async def update_profile(request: UpdateProfileRequest, current_user: User = Depends(get_current_user)):
    """Update user profile"""
    update_data = {}
    if request.full_name:
        update_data["full_name"] = request.full_name
    if request.phone:
        update_data["phone"] = request.phone
    if request.company:
        update_data["company"] = request.company
    if request.department:
        update_data["department"] = request.department
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.users.update_one({"id": current_user.id}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "hashed_password": 0})
    return User(**updated_user)


@router.put("/onboarding")
async def complete_onboarding(current_user: User = Depends(get_current_user)):
    """Mark user onboarding as complete"""
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"onboarding_completed": True}}
    )
    return {"message": "Onboarding completed"}


@router.post("/google")
async def google_auth(request: GoogleAuthRequest, response: Response):
    """Handle Google OAuth authentication via Emergent Auth"""
    try:
        # Get user info from Emergent Auth
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://auth.emergentagent.com/api/session/{request.session_id}",
                timeout=10.0
            )
            
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            session_data = resp.json()
            
        if not session_data or "user" not in session_data:
            raise HTTPException(status_code=401, detail="Invalid session data")
        
        google_user = session_data["user"]
        email = google_user.get("email", "").lower()
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": email}, {"_id": 0})
        
        if existing_user:
            # Update Google link status
            await db.users.update_one(
                {"email": email},
                {"$set": {
                    "google_linked": True,
                    "google_picture": google_user.get("picture"),
                    "full_name": google_user.get("name") or existing_user.get("full_name"),
                    "last_login": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            user = await db.users.find_one({"email": email}, {"_id": 0})
        else:
            # Check if this is an admin email
            is_admin = email in [e.lower() for e in ADMIN_EMAILS]
            
            if not is_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Account not found. Please contact your administrator to create an account."
                )
            
            # Create new admin user
            user = {
                "id": str(uuid.uuid4()),
                "email": email,
                "hashed_password": "",
                "full_name": google_user.get("name", email.split("@")[0]),
                "role": "admin",
                "google_linked": True,
                "google_picture": google_user.get("picture"),
                "onboarding_completed": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user)
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user["id"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        user_response = User(**{k: v for k, v in user.items() if k != "hashed_password"})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response.model_dump()
        }
        
    except httpx.RequestError as e:
        logger.error(f"Google auth request error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable")
    except Exception as e:
        logger.error(f"Google auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me/google-link-status")
async def get_google_link_status(current_user: User = Depends(get_current_user)):
    """Check if current user has linked Google account"""
    return {
        "google_linked": current_user.google_linked,
        "google_picture": current_user.google_picture
    }


@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user)):
    """Logout user (client should clear token)"""
    return {"message": "Logged out successfully"}
