"""
Security utilities for LeadGen Pro
JWT authentication, password hashing, and user verification
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

from core.config import JWT_SECRET, JWT_ALGORITHM
from core.database import db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Admin emails - these users always have admin privileges
ADMIN_EMAILS = ['mattmascasa@gmail.com', 'monika.iordanoff@gmail.com', 'admin@test.com']


class UserRole(str):
    ADMIN = "admin"
    CLIENT = "client"
    EMPLOYEE = "employee"


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    role: str
    company: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    onboarding_completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)


def is_admin_user(user: User) -> bool:
    """Check if user is an admin (by role or email)"""
    return user.role == "admin" or user.email in ADMIN_EMAILS


__all__ = [
    'pwd_context',
    'security',
    'ADMIN_EMAILS',
    'UserRole',
    'User',
    'verify_password',
    'get_password_hash',
    'get_current_user',
    'is_admin_user'
]
