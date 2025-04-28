# --- backend/app/models/conversation.py ---
from sqlalchemy import Column, String, DateTime, BigInteger, Integer, ForeignKey, Text, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List
import datetime

# Import Base from your db setup
# Assuming Base = declarative_base() is defined in app.db.base
try:
    from app.db.base import Base
except ImportError:
    # Fallback if running models standalone or different structure
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()


# --- SQLAlchemy Models ---

class Conversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    # Link to user if using authentication
    user_id = Column(BigInteger, index=True, nullable=False) # Assuming user ID is BigInteger
    service_name = Column(String, index=True, nullable=False) # e.g., "Technology Due Diligence"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at", lazy="selectin") # Eager load messages

class Message(Base):
    __tablename__ = "ai_messages"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(BigInteger, ForeignKey("ai_conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False) # "user" or "model" (or "ai")
    content = Column(LargeBinary, nullable=False) # Store compressed text as bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to conversation
    conversation = relationship("Conversation", back_populates="messages")


# --- Pydantic Schemas ---

class MessageBase(BaseModel):
    role: str = Field(..., pattern="^(user|model)$") # Validate role
    content: str # Use string for input/output

class MessageCreate(MessageBase):
    pass # Same fields needed to create

class MessageRead(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True # Pydantic v2 orm_mode

class ConversationRead(BaseModel):
    id: int
    user_id: int
    service_name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages: List[MessageRead] = [] # Include messages when reading conversation

    class Config:
        from_attributes = True

class PromptSuggestion(BaseModel):
     suggestions: List[str]

# Model for the modified AI Tool endpoint input
class AiChatQuery(BaseModel):
    user_query: str = Field(..., min_length=3, max_length=1500)
    service_name: str = Field(...) # Identify service context by name
    conversation_id: Optional[int] = None # To continue existing chat

# Model for the modified AI Tool endpoint response
class AiChatResponse(BaseModel):
    ai_response: str
    conversation_id: int # Always return the conversation ID
    error_message: Optional[str] = None