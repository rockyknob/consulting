# --- backend/app/models/user.py ---
from sqlalchemy import Column, String, DateTime, BigInteger, Boolean
from sqlalchemy.sql import func # For default timestamp
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional
import datetime

from app.db.base import Base # Import Base from base.py

# --- SQLAlchemy Model ---
class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    provider = Column(String, index=True, nullable=False) # 'google', 'linkedin', 'github'
    provider_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    display_name = Column(String, nullable=False)
    hashed_password: Optional[str] = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    # Add other fields like roles, preferences etc. if needed

# --- Pydantic Schemas ---

# Base properties shared by other schemas
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    profile_picture_url: Optional[HttpUrl] = None # Validate URL

# Properties received via API on creation (from OAuth profile)
class UserCreate(UserBase):
    provider: str
    provider_id: str
    display_name: str # Make display_name required on creation

# Properties to return to client (never return password hashes!)
class UserRead(UserBase):
    id: int # Use int for FastAPI response model
    provider: str
    provider_id: str # Might hide this in some contexts
    display_name: str
    created_at: datetime.datetime
    last_login: datetime.datetime

    class Config:
        orm_mode = True # Compatibility with SQLAlchemy models (Pydantic v1 style)
        # For Pydantic v2: from_attributes = True

# Properties stored in DB (could include hashed_password if doing local auth)
class UserInDBBase(UserBase):
    id: int
    provider: str
    provider_id: str
    created_at: datetime.datetime
    last_login: datetime.datetime

    class Config:
        orm_mode = True
        # For Pydantic v2: from_attributes = True

# Model for data sent from frontend Passport callback
class UserUpsertData(BaseModel):
    provider: str
    provider_id: str
    email: Optional[EmailStr] = None
    display_name: str
    profile_picture_url: Optional[HttpUrl] = None
class UserCreateLocal(BaseModel): # For local signup endpoint
    email: EmailStr
    password: str = Field(..., min_length=8) # Require password on signup
    display_name: str = Field(..., min_length=2)

class UserLogin(BaseModel): # For local login endpoint
    email: EmailStr # Or username if you prefer
    password: str