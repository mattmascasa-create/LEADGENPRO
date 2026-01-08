"""
Authentication Routes - Login, Register, Profile, and Google OAuth
"""

import os
import re
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
import jwt

from models.schemas import User, UserCreate, UserLogin, Token, GoogleAuthRequest
from services.database import db
from services.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, JWT_SECRET, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Emergent Auth URL
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


class UpdateProfileRequest(BaseModel):
    phone: Optional[str] = None
    full_name: Optional[str] = None
    company: Optional[str] = None
    department: Optional[str] = None


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    """Register a new user"""
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.model_dump(exclude={"password"})
    user = User(**user_dict)
    
    doc = user.model_dump()
    doc['password'] = get_password_hash(user_data.password)
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login with email and password"""
    user_doc = await db.users.find_one({"email": credentials.email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user_doc['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**{k: v for k, v in user_doc.items() if k != 'password'})
    
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.put("/profile")
async def update_profile(request: UpdateProfileRequest, current_user: User = Depends(get_current_user)):
    """Update current user's profile including phone number for click-to-call"""
    update_data = {}
    if request.phone is not None:
        phone = request.phone
        if phone and not phone.startswith('+'):
            digits = re.sub(r'\D', '', phone)
            if len(digits) == 10:
                phone = '+1' + digits
            elif len(digits) == 11 and digits.startswith('1'):
                phone = '+' + digits
        update_data["phone"] = phone
    if request.full_name is not None:
        update_data["full_name"] = request.full_name
    if request.company is not None:
        update_data["company"] = request.company
    if request.department is not None:
        update_data["department"] = request.department
    
    if update_data:
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": update_data}
        )
    
    updated_user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "hashed_password": 0})
    return updated_user


@router.put("/onboarding")
async def complete_onboarding(current_user: User = Depends(get_current_user)):
    """Mark onboarding as completed"""
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"onboarding_completed": True}}
    )
    return {"message": "Onboarding completed"}


@router.post("/google")
async def google_auth(request: GoogleAuthRequest, response: Response):
    """
    Process Google OAuth session from Emergent Auth.
    Only allows sign-in if user already exists (admin must create account first).
    """
    try:
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                EMERGENT_AUTH_URL,
                headers={"X-Session-ID": request.session_id},
                timeout=30
            )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        session_data = auth_response.json()
        google_email = session_data.get("email")
        google_name = session_data.get("name")
        google_picture = session_data.get("picture")
        session_token = session_data.get("session_token")
        
        if not google_email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        existing_user = await db.users.find_one({"email": google_email}, {"_id": 0})
        
        if not existing_user:
            raise HTTPException(
                status_code=403, 
                detail="No account found with this email. Please contact your administrator to create an account first."
            )
        
        update_data = {
            "google_linked": True,
            "google_picture": google_picture,
            "last_login": datetime.now(timezone.utc).isoformat()
        }
        
        if not existing_user.get("full_name") and google_name:
            update_data["full_name"] = google_name
        
        await db.users.update_one(
            {"email": google_email},
            {"$set": update_data}
        )
        
        await db.google_sessions.update_one(
            {"user_id": existing_user["id"]},
            {
                "$set": {
                    "user_id": existing_user["id"],
                    "session_token": session_token,
                    "google_email": google_email,
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        token_data = {"sub": existing_user["id"], "email": google_email}
        access_token = jwt.encode(
            {**token_data, "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 48)},
            JWT_SECRET,
            algorithm=ALGORITHM
        )
        
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=7 * 24 * 60 * 60
        )
        
        user = await db.users.find_one({"id": existing_user["id"]}, {"_id": 0, "hashed_password": 0})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
            "message": "Successfully signed in with Google"
        }
        
    except httpx.RequestError as e:
        logging.error(f"Error contacting Emergent Auth: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable")


@router.get("/me/google-link-status")
async def get_google_link_status(current_user: User = Depends(get_current_user)):
    """Check if user has linked their Google account for sign-in"""
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    google_session = await db.google_sessions.find_one({"user_id": current_user.id}, {"_id": 0})
    
    return {
        "google_linked": user.get("google_linked", False),
        "google_picture": user.get("google_picture"),
        "session_valid": google_session is not None
    }


@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user)):
    """Logout and clear session"""
    await db.google_sessions.delete_one({"user_id": current_user.id})
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Successfully logged out"}


@router.get("/check-admin")
async def check_admin_status(current_user: User = Depends(get_current_user)):
    """Check if current user has admin privileges"""
    from services.auth import is_admin_user
    return {
        "is_admin": is_admin_user(current_user),
        "role": current_user.role,
        "email": current_user.email
    }
