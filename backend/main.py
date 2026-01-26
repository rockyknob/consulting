# --- backend/main.py ---
# Single file implementation including all features.
# WARNING: Uses temporary in-memory storage for tracking and
# non-persistent CSV file saving for submissions on most free hosting.
# DATABASE INTEGRATION IS REQUIRED FOR PRODUCTION DEPLOYMENT.

import fastapi
from fastapi import FastAPI, HTTPException, status, Query, UploadFile, File, APIRouter, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from app.db.database import get_db
from app.models.analysis import IndustryIntel # Import the intel model if using backend processing
import datetime
import os
import csv
import logging
import zlib
from dotenv import load_dotenv
import uuid
from typing import List, Dict, Any, Optional, Tuple
import traceback
import io
from app.models.conversation import Conversation, Message
from app.models import conversation as conv_models
from app.services import conversation_service
import pandas as pd
import re
import zipfile
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Column, String, DateTime, BigInteger, Boolean, select, func # Ensure needed imports are here or at top
from sqlalchemy.orm import sessionmaker, declarative_base
# --- Add near top of backend/main.py ---
from passlib.context import CryptContext
from app.core.config import settings # Import settings from configbcryp
import logging
from sqlalchemy.future import select
from app.models import user as user_models # Pydantic schemas (use alias if needed)
# --- >>> THIS IS THE CORRECTED LINE <<< ---
from app.models.user import User as UserModel
import json
from sqlalchemy import Column, String, DateTime, BigInteger, Integer, ForeignKey, Text, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from fastapi.security import OAuth2PasswordBearer
import re
import google.generativeai as genai

# 1. Configure with your API Key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# Secure file upload validation
ALLOWED_EXTENSIONS = {'txt', 'csv', 'xlsx', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_upload(file: UploadFile):
    # Validate extension
    if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(400, "Invalid file type")
    
    # Validate size
    file.file.seek(0, 2)
    size = file.file.tell()
    if size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    file.file.seek(0)
    
    # Sanitize filename
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
    return filename

# Authentication middleware
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Implement JWT validation logic
    return user
# Import SQLAlchemy User model from models/user.py



# Needed by python-docx check below

# --- Setup ---
# Load .env file from backend directory (relative to this file)
load_dotenv(dotenv_path='.env')
print(f"Attempting to load .env file from backend directory...")
print(f"FRONTEND_URL from env: {os.getenv('FRONTEND_URL')}") # Debug print
print(f"GOOGLE_API_KEY from env: {'Exists' if os.getenv('GOOGLE_API_KEY') else 'MISSING!'}") # Debug print

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- AI Library & Docx Import (Conditional) ---
AI_LIB_AVAILABLE = False
DOCX_LIB_AVAILABLE = False
try:
    import google.generativeai as genai
    AI_LIB_AVAILABLE = True
    logger.info("google-generativeai library found.")
except ImportError:
    genai = None
    logger.warning("google-generativeai library not found. AI features disabled.")

try:
    import docx
    DOCX_LIB_AVAILABLE = True
    logger.info("python-docx library found.")
except ImportError:
    docx = None # Make docx variable None if import fails
    logger.warning("python-docx library not found. DOCX parsing will be disabled.")


# --- Data Storage Configuration & In-Memory Store ---
# !! WARNING: Data stored here/CSV is TEMPORARY / EPHEMERAL !!
request_store: List[Dict[str, Any]] = [] # In-memory for contact tracking
DATABASE_URL = os.getenv("DATABASE_URL")
engine = None           # Define BEFORE try block
AsyncSessionLocal = None # Define BEFORE try block
Base = declarative_base()
# Path relative to where uvicorn runs (assume project root -> backend/data_storage)
# Or make absolute: DATA_DIR = os.path.join(os.path.dirname(__file__), "data_storage")
DATA_DIR = "data_storage" # Simpler if running uvicorn from backend/ dir
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.csv")
HIRE_REQUESTS_FILE = os.path.join(DATA_DIR, "hire_requests.csv")
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info(f"Data storage directory '{os.path.abspath(DATA_DIR)}' ensured.")
except OSError as e:
    logger.error(f"Could not create data storage directory '{DATA_DIR}': {e}")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

logger.info("Password hashing utilities defined.")

# --- Pydantic Models ---
class ContactFormInput(BaseModel): name: str; email: EmailStr; company: Optional[str] = None; phone: Optional[str] = None; subject: str; message: str
class ContactSubmitResponse(BaseModel): message: str; request_id: str; status: str
class TrackedRequest(BaseModel): request_id: str; timestamp: datetime.datetime; status: str; subject: str
class TrackingResponse(BaseModel): identifier: str; requests: List[TrackedRequest]
class HireConsultantForm(BaseModel): contact_name: str = Field(...); contact_email: EmailStr; contact_phone: Optional[str] = None; contact_company: Optional[str] = None; industry: str = Field(...); business_function: str = Field(...); services_needed: List[str] = Field([]); project_timeline: str = Field(...); start_date: Optional[datetime.date] = None; resources_required: Optional[str] = None; location: Optional[str] = None; work_type: str = Field(...); experience_needed: Optional[str] = None; skills_needed: Optional[str] = None; project_description: str = Field(..., min_length=10)
class HireSubmitResponse(BaseModel): message: str; hire_request_id: str; status: str
class AiToolQuery(BaseModel): user_query: str = Field(..., min_length=5, max_length=1500); service_context: Dict[str, Any] = Field(...)
class AiToolResponse(BaseModel): ai_response: str; error_message: Optional[str] = None
# --- Pydantic Models ---
logger.info("Defining Pydantic models...") # Add log to confirm execution

class ContactFormInput(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    subject: str
    message: str

class ContactSubmitResponse(BaseModel):
    message: str
    request_id: str
    status: str

class TrackedRequest(BaseModel):
    request_id: str
    timestamp: datetime.datetime
    status: str
    subject: str

class TrackingResponse(BaseModel):
    identifier: str
    requests: List[TrackedRequest]

class HireConsultantForm(BaseModel):
    contact_name: str = Field(...)
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    contact_company: Optional[str] = None
    industry: str = Field(...)
    business_function: str = Field(...)
    services_needed: List[str] = Field([])
    project_timeline: str = Field(...)
    start_date: Optional[datetime.date] = None
    resources_required: Optional[str] = None
    location: Optional[str] = None
    work_type: str = Field(...)
    experience_needed: Optional[str] = None
    skills_needed: Optional[str] = None
    project_description: str = Field(..., min_length=10)

class HireSubmitResponse(BaseModel):
    message: str
    hire_request_id: str
    status: str

class StartupInput(BaseModel): # Includes Berkus fields
    company_name: str = Field(..., examples=["Acme Widgets"])
    industry: str = Field(..., examples=["SaaS", "E-commerce", "Biotech"])
    stage: str = Field(..., examples=["Seed", "Series A"]) # ADDED field
    problem_solved: str = Field(..., min_length=10, examples=["Finding qualified dog walkers reliably."]) # ADDED field
    solution: str = Field(..., min_length=10, examples=["An app connecting owners with vetted walkers."]) # ADDED field
    target_market: str = Field(..., min_length=10, examples=["Busy professionals in urban areas."]) # ADDED field
    business_model: str = Field(..., min_length=10, examples=["Commission on bookings, premium subscription."]) # ADDED field
    description: str = Field(..., min_length=20, examples=["Our vision is to..."]) # General Description

    # Optional Details
    team_size: Optional[int] = Field(default=1, ge=1)
    funding_raised_usd: Optional[float] = Field(default=0, ge=0)
    key_competitors: Optional[str] = Field(default=None)
    # Optional metrics (were in older model, useful context if provided by form)
    monthly_recurring_revenue: Optional[float] = Field(default=0, ge=0)
    customer_metric: Optional[str] = Field(default=None)

    # Berkus Method Fields
    has_prototype: bool = Field(False, description="Does the startup have a working prototype or MVP?")
    management_summary: Optional[str] = Field(None, max_length=1000, description="Brief summary of management team's experience and completeness.")
    strategic_partnerships: Optional[str] = Field(None, max_length=1000, description="Describe key strategic relationships or early adopters secured.")
    sales_traction_summary: Optional[str] = Field(None, max_length=1000, description="Describe initial product rollout status or early sales traction.")


class StartupAnalysisResult(BaseModel): # Updated Response Model
    analysis_text: Optional[str] = None # Holds the main AI text (Berkus, SWOT, etc.)
    processing_status: str = "Completed"
    # NEW fields for fetched intelligence:
    industry_reports: Optional[List[IndustryIntel]] = None
    latest_news: Optional[List[IndustryIntel]] = None
    recent_deals: Optional[List[IndustryIntel]] = None
    # Keep standard fields
    disclaimer: str = "AI analysis uses internal knowledge & limited external search. Info may be incomplete or dated. Valuations are estimates. Consult human experts."
    error_message: Optional[str] = None

# --- User Models (Needed for Endpoints) ---
class UserBase(BaseModel): # Base schema for shared properties
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    profile_picture_url: Optional[HttpUrl] = None

class UserCreate(UserBase): # Schema for creating via service
    provider: str
    provider_id: str
    display_name: str # Required on creation

class UserRead(UserBase): # Schema for returning user data from API
    id: int # Internal DB ID
    provider: str
    # provider_id: str # Maybe hide this?
    display_name: str # Ensure it's required here if non-optional in DB model
    created_at: datetime.datetime
    last_login: datetime.datetime

    # If using SQLAlchemy models & returning them directly (needs DB setup)
    # class Config:
    #     orm_mode = True # Pydantic v1
    #     # from_attributes = True # Pydantic v2

class UserUpsertData(BaseModel): # Data received from frontend Passport callback
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
    conversation_id: Optional[int] = None

# Model for the modified AI Tool endpoint response
class AiChatResponse(BaseModel):
    ai_response: str
    conversation_id: int # Always return the conversation ID
    error_message: Optional[str] = None
# --- Static Content Data Definitions ---
# (Keep all data lists/dicts here as defined in Response #93)

logger.info("Defining Conversation/Message SQLAlchemy models...")

logger.info("Conversation/Message SQLAlchemy models defined.")

# --- Setup ---
# Load .env file relative to where uvicorn is run (usually project root)
load_dotenv(dotenv_path='backend/.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- AI Library Import (Conditional) ---
AI_LIB_AVAILABLE = False
try:
    import google.generativeai as genai
    AI_LIB_AVAILABLE = True
    logger.info("google-generativeai library found.")
except ImportError:
    genai = None
    logger.warning("google-generativeai library not found. AI features disabled.")

# --- Data Storage Configuration & In-Memory Store ---
# !! WARNING: Data stored here/CSV is TEMPORARY / EPHEMERAL !!
request_store: List[Dict[str, Any]] = [] # In-memory for contact tracking

DATA_DIR = os.path.join("backend", "data_storage") # Path relative to project root
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.csv")
HIRE_REQUESTS_FILE = os.path.join(DATA_DIR, "hire_requests.csv")
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info(f"Data storage directory '{DATA_DIR}' ensured.")
except OSError as e:
    logger.error(f"Could not create data storage directory '{DATA_DIR}': {e}")


# --- Pydantic Models ---



# --- Static Content Data Definitions ---
# (Ideally load from file/DB)
hero_content = {
    "headline": "Smarten your Future",
    "subheadline": "Partnering with industry leaders to solve complex business challenges and unlock value through data-driven decision making and digital innovation.",
    "cta_button_text": "Discover Our Products",
    "cta_link": "#services",
    "background_image_placeholder": "https://source.unsplash.com/1600x900/?business,technology,abstract"
}

services_data = [
    {
        "title": "Strategy Development", "icon": "fas fa-lightbulb",
        "description": "Navigate market shifts and achieve sustainable growth with future-proof strategies and organizational redesign.",
        "img_placeholder": "https://placehold.co/350x200/003087/FFFFFF?text=Strategy"
    },
    {
        "title": "Digital Transformation", "icon": "fas fa-rocket",
        "description": "Leverage cutting-edge technology, AI, and data analytics to optimize operations, enhance customer engagement, and build digital-native capabilities.",
        "img_placeholder": "https://placehold.co/350x200/007bff/FFFFFF?text=Digital"
    },
    {
        "title": "Performance and Cost Optimization", "icon": "fas fa-chart-line",
        "description": "Unlock hidden value through operational excellence, cost optimization, and process re-engineering for measurable bottom-line impact.",
        "img_placeholder": "https://placehold.co/350x200/6c757d/FFFFFF?text=Performance"
    }
    # Add more services if you have them
]

clients_data = [
    {"name": "Global Tech Corp", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Global+Tech"},
    {"name": "Innovate Pharma", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Innovate"},
    {"name": "Quantum Finance", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Quantum"},
    {"name": "Apex Manufacturing", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Apex+Mfg"},
    {"name": "NextGen Retail", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=NextGen"},
    {"name": "Synergy Energy", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Synergy"}
    # Add more clients if you have them
]

testimonials_data = [
     {
        "quote": "ZAlpha's insights into digital transformation were instrumental in reshaping our customer experience and driving significant growth. Their team is world-class.",
        "author": "Eleanor Vance",
        "title": "Chief Technology Officer, Global Tech Corp"
     },
     {
        "quote": "The operational efficiency program designed by ZAlpha delivered results beyond our expectations, streamlining processes and improving our bottom line.",
        "author": "Kenji Tanaka",
        "title": "VP Operations, Apex Manufacturing"
     },
     {
        "quote": "Their strategic guidance helped us navigate a complex market entry. We felt supported and confident with ZAlpha as our partner.",
        "author": "Aisha Khan",
        "title": "Head of Strategy, Innovate Pharma"
     }
     # Add more testimonials if you have them
]

products_data = [
    {
        "id": "prod_ai_analyzer", "name": "Financial Analyzer",
        "tagline": "Derive insights from your financial data.",
        "description": "Upload your P&L or other statements (.xlsx, .csv, .docx, .txt) for automated insights and conceptual SWOT analysis. (Beta)",
        "img_placeholder": "https://placehold.co/350x200/0056b3/FFFFFF?text=AI+Analyzer",
        "link": "/financial-analyzer"
    },
    {
        "id": "prod_startup_consult", "name": "Startup Consultation",
        "tagline": "Know Your Business.",
        "description": "Input key metrics about your startup for intelligent consultation on strategy, risks, opportunities, and valuation factors. Includes placeholder reports & case studies. (Beta)",
        "img_placeholder": "https://placehold.co/350x200/17a2b8/FFFFFF?text=Startup+AI",
        "link": "/startup-consultation"
    },
    {
        "id": "prod_custom_solution", "name": "Custom Consulting Solutions",
        "tagline": "Tailored strategies for your unique challenges.",
        "description": "Leverage our expert consultants for bespoke solutions in strategy, digital transformation, performance optimization, and more. Contact us.",
        "img_placeholder": "https://placehold.co/350x200/ffc107/000000?text=Custom",
        "link": "/custom-consulting"
    }
    # Add more products if you have them
]
custom_consulting_packages = [
    {
        "id": "tech_dd",
        "name": "Technology Due Diligence",
        "description": "Our areas of concentration cover the team, the product, platform architecture and the infrastructure of the target company highlighting possible issues that could put our clients at risk. Our goal is to remain unbiasedly identify potential risks and offer insights that allow clients to make the best decisions.",
        "deliverables": [
            "Technical assessment overview",
            "Technology and Architecture review",
            "Platform Scalability analysis",
            "Code review and quality assessment",
            "Infrastructure and DevOps assessment",
            "Product and UX/UI review/assessment", # Combined for brevity
            "Customer surveys",
            "Risk assessment",
            "Action Plan"
        ],
        "documents": [
            "Executive Summary containing impactful information from the insights gathered through overall technical due diligence that influence summary findings.",
            "Data databook outlining detailed data points and data management plan as well as supporting documentation.",
            "Action items and points having a comprehensive list of areas that require improvement from the product/service offered and technology and changes for improvement in the digital strategy."
        ],
        "icon": "fas fa-cogs" # Example icon
    },
    {
        "id": "cdd",
        "name": "Commercial Due Diligence (CDD)",
        "description": "CDD provides the client with a comprehensive understanding of the target company's commercial position, market dynamics, and growth prospects. They enable the client to assess the attractiveness of the deal, independently evaluate potential synergies, and make informed decisions regarding the transaction.",
        "deliverables": [
            "Market Analysis Report",
            "Competitive Landscape Assessment",
            "Customer Analysis",
            "Revenue and Financial Analysis",
            "Management/Team Assessment", # Combined/simplified
            "Team Capabilities",
            "Growth Strategy",
            "Commercial Due Diligence Summary",
            "Action plan"
        ],
        "documents": [
            "Detailed report containing detailed investment thesis with outputs driven from completed data points (interviews, surveys, analysis and report).",
            "Complete Databook containing all insights gathered via the CDD engagement.",
            "Executive summary marketing financial outputs captured from the steps followed in the engagement including summary financials.",
            "Excel file work outlining detailed financial and operational plan as well as having data models showing revenue and financial analysis, business valuation summary and output.",
            "Action items and pain points having a comprehensive list of areas that require improvement from the product/service offered and technology and changes for improvement."
        ],
         "icon": "fas fa-briefcase"
    },
    {
        "id": "investor_pres",
        "name": "Investor Presentation",
        "description": "Our investor presentation service help you position business right before investor and raise your next funding round.",
        "deliverables": [
            "Pitch Deck Audit",
            "Executive Summary",
            "Value Proposition",
            "Market Analysis",
            "Product Strategy",
            "Business Model and Revenue Generation",
            "Financial Projections",
            "Fundraising Strategy",
            "Use of Funds",
            "Action plan"
        ],
        "documents": [
            "Investment Thesis outlining investment hypothesis and quantitative estimation of the the opportunity size covering TAM, SAM, SOM.",
            "An Investor pitch deck containing information about company overview, market, product/service description, analysis, unique selling points, business model analysis as well as revenue generation plans.",
            "An action plan containing each databook providing detailed financial projections, detailed revenue structure, expense projections and cash flow analysis."
        ],
         "icon": "fas fa-file-powerpoint"
    },
    {
        "id": "gtm_strategy",
        "name": "Go To Market Strategy",
        "description": "The goal of Go-To-Market strategy package is to develop a comprehensive plan that maximises the chances of success for a new product or service while minimizing the risk of failure.",
        "deliverables": [
            "Business Analysis",
            "Market Research and Analysis",
            "Customer Segmentation and Targeting",
            "Competitive Benchmarking",
            "Marketing and Sales Strategy/Framework", # Combined
            "Pricing and operational model/support Plan", # Combined
            "Metrics and KPIs",
            "GTM Plan Executive Summary"
        ],
        "documents": [
            "Detailed GTM strategy report containing identifiable outputs driven from comprehensive business analysis, market research and analysis report.",
            "A complete data book from the marketing and sales outlining the framework.",
            "A complete financial model outlining the marketing and sales team budget and deep dive financial analysis as well as overall cost analysis and market prioritization report.",
            "Action plan documents having a detailed pricing and operational launch plan, metrics as well as having data models showing critical financial metrics and KPIs.",
            "Action items and pain points having a comprehensive list of areas that require improvement from the product/service offered and technology and changes for improvement in the overall business strategy."
        ],
         "icon": "fas fa-rocket"
    },
    {
        "id": "fin_modeling",
        "name": "Financial Modeling",
        "description": "Financial data and calculations can be used for purposes such as valuation, budgeting, forecasting, risk management, financial planning, and investment analysis.",
        "deliverables": [
            "Financial Model for startup fundraising",
            "M&A Modeling",
            "Functional Budgeting & KPIs",
            "Operational Modeling",
            "Cash Flow Analysis",
            "Valuation Modeling",
            "Financial KPIs",
            "Investor Report (incl. Model)",
            "Financial Presentation to Board"
        ],
        "documents": [
            "An excel file containing each databook providing detailed projection of the financial structure along with sensitivity analysis. Model output includes revenue forecast, expense projections, and cash flow analysis.",
            "Financial model output including 3-statement financial model with discount, WACC assumption, Multiples, DCF, IRR and ARR as well as other financial metrics.",
            "Detailed Financial plan containing Financial highlights and narrative."
        ],
         "icon": "fas fa-calculator"
    },
     {
        "id": "cap_table",
        "name": "Cap Table Simulation",
        "description": "A Cap Table simulation analyzes different funding scenarios.", # Simplified description
        "deliverables": [
            "Cap table Simulation Report",
            "Waterfall Analysis (incl. Sensitivity Analysis)",
            "Shareholder Analysis",
            "Investor Analysis",
            "Valuation Assessment",
            "Sensitivity Analysis",
            "Final output"
        ],
        "documents": [
            "Detailed cap table with scenarios.",
            "Convertible debt/equity simulation document to capture investment amount, valuation cap, discount & interest, issued/unissued shares to round.",
            "Leading ESOP simulation.",
            "Profit sharing distribution model based on pre/post round valuation assumptions."
        ],
         "icon": "fas fa-table"
    },
    {
        "id": "ux_audit",
        "name": "UX Audit Service",
        "description": "Our areas of concentration are product, team, platform understanding and the infrastructure. Highlighting possible issues that could put our clients at risk. Our goal is to remain unbiasedly identify potential risks and offer insights that allow clients to make the best decisions.", # Description seems similar to Tech DD, adjust if needed
        "deliverables": [
            "Platform Understanding",
            "User Workflow Analysis/Maps", # Combined
            "Heuristic Evaluation",
            "Accessibility (WCAG) Analysis",
            "Customer Journey Mapping",
            "User Testing",
            "Final output",
            "Action Plan"
        ],
        "documents": [
            # Assuming similar output types to Tech DD but focused on UX
            "Executive Summary of UX findings and strategic recommendations.",
            "Detailed UX Audit Report outlining issues, heuristics violations, accessibility gaps.",
            "User journey maps and workflow analysis documentation.",
            "User testing results synthesis.",
            "Prioritized action plan for UX improvements."
        ],
         "icon": "fas fa-search-plus"
    }
    # Add more packages as needed
]


# --- AI Configuration ---
ai_model = None
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if AI_LIB_AVAILABLE and GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        ai_model = genai.GenerativeModel(model_name="gemini-3-flash-preview")
        logger.info("Gemini AI Model configured successfully.")
    except Exception as e: logger.error(f"Error configuring Gemini AI Model: {e}", exc_info=True); ai_model = None
else: logger.warning("AI Service disabled (check API key in .env & google-generativeai install).")


# --- FastAPI App Instance Definition ---
app = FastAPI(title="ZAlpha Consulting Backend API")

# --- Add/Update in User Service Functions section of main.py ---
DATABASE_URL = str(settings.DATABASE_URL) # Ensure it's a string
if not DATABASE_URL:
    logger.error("FATAL: DATABASE_URL not found in environment variables!")
    # Optionally raise an error to prevent startup without DB URL
    # raise ValueError("DATABASE_URL environment variable must be set.")
    engine = None
    AsyncSessionLocal = None
else:
    if "?" in DATABASE_URL:
        # If other query params exist, append with &
        db_url_for_engine = f"{DATABASE_URL}&prepared_statement_cache_size=0"
    else:
        # Otherwise, start query params with ?
        db_url_for_engine = f"{DATABASE_URL}?prepared_statement_cache_size=0"
    # Ensure the URL starts with postgresql+asyncpg:// for SQLAlchemy async engine
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not DATABASE_URL.startswith("postgresql+asyncpg://"):
         logger.error(f"FATAL: DATABASE_URL has unexpected scheme: {DATABASE_URL}")
         raise ValueError("DATABASE_URL must start with postgresql:// or postgresql+asyncpg://")

    logger.info(f"Database URL found: {'...' + DATABASE_URL[-20:]}") # Log partial URL

    try:
        # Create Async Engine
        engine = create_async_engine(
            DATABASE_URL,
            echo=False, # Set to True for SQL query logging (noisy)
            pool_pre_ping=True,
            pool_recycle=300,  # Close and reopen connections every 5 mins
    connect_args={
        "command_timeout": 60, # Give the connection more time to breathe
        }
        )

        # Create Async SessionLocal class factory
        AsyncSessionLocal = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        logger.info("SQLAlchemy async engine and session maker configured.")

    except Exception as e:
         logger.error(f"FATAL: Failed to configure SQLAlchemy engine/session: {e}", exc_info=True)
         engine = None
         AsyncSessionLocal = None
         # Raise error to prevent startup if DB connection fails
         raise RuntimeError(f"Database configuration failed: {e}")


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields an async database session.
    Ensures the session is closed even if errors occur.
    """
    if AsyncSessionLocal is None:
         logger.error("Database session not configured. Cannot get DB session.")
         raise HTTPException(status_code=503, detail="Database connection not available.")

    async with AsyncSessionLocal() as session:
        logger.debug(f"DB Session {id(session)} acquired.")
        try:
            yield session
            # Commit is usually handled by the endpoint logic after using the session
            # await session.commit() # Avoid double commits, handle in endpoint/service
        except Exception as e:
             logger.error(f"DB Session {id(session)} rollback due to exception: {e}", exc_info=True)
             await session.rollback()
             raise # Re-raise the exception for FastAPI to handle
        finally:
             logger.debug(f"DB Session {id(session)} closed.")
             await session.close()
# --- CORS Middleware ---
default_frontend_url = "http://localhost:3000"
frontend_url_from_env = os.getenv("FRONTEND_URL", default_frontend_url)
origins = list(set(["https://consulting-1-u97v.onrender.com", "http://localhost:3001"] + os.getenv("EXTRA_ALLOWED_ORIGINS", "").split(',')))
origins = [o.strip() for o in origins if o]
logger.info(f"Configuring CORS for origins: {origins}")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])


# --- Helper Functions ---
def save_to_csv(filepath: str, fieldnames: List[str], row_data: Dict[str, Any]):
    """Generic helper to append a row to CSV. Returns True on success."""
    # No need to ensure dir here if done on startup, but doesn't hurt
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file_exists = os.path.isfile(filepath)
    try:
        with open(filepath, mode='a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            if not file_exists or os.path.getsize(filepath) == 0: writer.writeheader()
            csv_row = {field: str(row_data.get(field, "")).replace('\n', '\\n') for field in fieldnames}
            writer.writerow(csv_row)
        logger.info(f"Data successfully saved to {os.path.basename(filepath)}")
        return True
    except Exception as e: logger.error(f"Error writing CSV {filepath}: {e}", exc_info=True); return False

# --- AI Service Functions ---
STARTUP_ANALYSIS_TEMPLATE = """Analyze {company} using:
- Berkus Method (prototype: {prototype}, management: {management})
- Market potential: {market}
- SWOT analysis
- Valuation drivers

Keep analysis concise with bullet points. Highlight key risks and opportunities."""

async def get_startup_analysis(startup_data: StartupInput) -> str:
    try:
        prompt = STARTUP_ANALYSIS_TEMPLATE.format(
            company=startup_data.company_name,
            prototype=startup_data.has_prototype,
            management=startup_data.management_summary[:500] if startup_data.management_summary else 'None provided',
            market=startup_data.target_market
        )
        response = await ai_model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Startup analysis failed: {str(e)}")
        return f"Analysis error: {str(e)}"

# --- API Endpoints ---
API_V1_STR = "/api/v1" # Define prefix
@app.post(
    f"{API_V1_STR}/users/find-or-create", # Path must match exactly
    response_model=UserRead, # Pydantic response model
    status_code=status.HTTP_200_OK,
    summary="Find or Create User from OAuth",
    tags=["Users & Auth"]
)
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
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Finds a user by their email address."""
    logger.info(f"Querying user by email: {email}")
    statement = select(User).where(User.email == email.lower()) # Store/query email lowercase
    result = await db.execute(statement)
    user = result.scalar_one_or_none()
    if user: logger.info(f"User found for email {email}: ID {user.id}")
    else: logger.info(f"User NOT found for email {email}")
    return user

# Modify create_user or add create_local_user
async def create_local_user(db: AsyncSession, *, user_in: UserCreateLocal) -> User:
    """Creates a new user with email/password (local provider)."""
    logger.info(f"Creating new local user for email={user_in.email}")
    hashed_pw = hash_password(user_in.password)
    # Use email or generate unique ID for provider_id for local users? Using email for now.
    provider_id_for_local = f"local|{user_in.email.lower()}"

    db_user = User(
        provider="local", # Indicate local provider
        provider_id=provider_id_for_local,
        email=user_in.email.lower(), # Store email lowercase
        display_name=user_in.display_name,
        hashed_password=hashed_pw
    )
    db.add(db_user)
    try:
        await db.flush() # Try flushing first to catch unique constraint errors
        await db.refresh(db_user)
        logger.info(f"Local user created successfully with ID: {db_user.id}")
        return db_user
    except Exception as e: # Catch potential DB errors (like unique email violation)
         await db.rollback() # Rollback before re-raising
         logger.error(f"DB error creating local user {user_in.email}: {e}", exc_info=True)
         # Re-raise a more specific error maybe? For now, just raise original
         raise e
async def endpoint_find_or_create_user( # Function name can vary
    user_data: UserUpsertData, # Pydantic input model
    db: AsyncSession = Depends(get_db) # Assuming get_db dependency works
    ):
    logger.info(f"Endpoint: /users/find-or-create called for provider={user_data.provider}")
    try:
        # Make sure user_service functions are defined above or imported
        user = await get_or_create_user(db=db, user_data=user_data) # Call helper/service
        if not user:
             raise HTTPException(status_code=500, detail="Failed to process user login.")
        logger.info(f"Returning user data for ID: {user.id}")
        return user # Return the Pydantic model compatible object/dict
    except Exception as e:
        logger.error(f"Error in find_or_create_user_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error during user processing: {e}")

@app.get(f"{API_V1_STR}/content", status_code=status.HTTP_200_OK, tags=["Content"])
async def endpoint_get_website_content():
    logger.info(f"GET {API_V1_STR}/content requested")
    # Return data defined globally
    return { "hero": hero_content, "services": services_data, "clients": clients_data, "testimonials": testimonials_data, "products": products_data, "custom_consulting_packages": custom_consulting_packages, "current_year": datetime.datetime.now().year }

@app.post(f"{API_V1_STR}/auth/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED, tags=["Users & Auth"])
async def signup_local_user(
    user_in: UserCreateLocal,
    db: AsyncSession = Depends(get_db)
    ):
    """Handles local user registration."""
    logger.info(f"POST /auth/signup received for email: {user_in.email}")
    existing_user = await get_user_by_email(db, email=user_in.email.lower())
    if existing_user:
        logger.warning(f"Signup attempt for existing email: {user_in.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )
    try:
        new_user = await create_local_user(db=db, user_in=user_in)
        # Exclude sensitive info for the response automatically via UserRead model
        return new_user # FastAPI converts SQLAlchemy User -> Pydantic UserRead
    except Exception as e: # Catch potential errors during creation
        logger.error(f"Error during signup for {user_in.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not create user account.")

async def get_user_by_provider_id(db: AsyncSession, *, provider: str, provider_id: str) -> Optional[UserModel]:
    """Finds a user by their OAuth provider and provider-specific ID."""
    logger.info(f"Querying user by provider={provider}, provider_id={provider_id[:5]}...")
    statement = select(UserModel).where(UserModel.provider == provider, UserModel.provider_id == provider_id)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()
    if user:
        # Update last login time on fetch
        user.last_login = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(user)
        logger.info(f"User found for provider={provider}, provider_id={provider_id[:5]}...")
    else:
        logger.info(f"User NOT found for provider={provider}, provider_id={provider_id[:5]}...")
    return user

async def create_user(db: AsyncSession, *, user_in: user_models.UserCreate) -> UserModel:
    """Creates a new user in the database."""
    logger.info(f"Creating new user for provider={user_in.provider}, email={user_in.email}")
    db_user = UserModel(
        provider=user_in.provider,
        provider_id=user_in.provider_id,
        email=str(user_in.email) if user_in.email else None, # Ensure email is string or None
        display_name=user_in.display_name,
        profile_picture_url=str(user_in.profile_picture_url) if user_in.profile_picture_url else None # Ensure URL is string or None
        # created_at and last_login have defaults
    )
    db.add(db_user)
    await db.commit() # Commit to get the ID generated by DB
    await db.refresh(db_user) # Refresh to load default values like ID, created_at
    logger.info(f"User created successfully with ID: {db_user.id}")
    return db_user

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[UserModel]:
    """Finds a user by their internal database ID."""
    logger.info(f"Querying user by internal ID: {user_id}")
    statement = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()
    if user: logger.info(f"User found for ID {user_id}")
    else: logger.info(f"User NOT found for ID {user_id}")
    return user

@app.post(f"{API_V1_STR}/auth/login", response_model=UserRead, status_code=status.HTTP_200_OK, tags=["Users & Auth"])
async def login_local_user(
    form_data: UserLogin, # Use specific login model
    db: AsyncSession = Depends(get_db)
    ):
    """Validates local user credentials. Called by frontend Passport local strategy."""
    logger.info(f"POST /auth/login attempt for email: {form_data.email}")
    user = await get_user_by_email(db, email=form_data.email.lower())

    if not user or user.provider != "local" or not user.hashed_password:
        logger.warning(f"Login failed (user not found or not local auth): {form_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.", # Keep error generic
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Login failed (incorrect password): {form_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- Password verified ---
    # Update last login time
    user.last_login = datetime.datetime.now(datetime.timezone.utc)
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback() # Rollback on update error
        logger.error(f"Failed to update last_login for user {user.id}: {e}", exc_info=True)
         # Log error but proceed with login

    logger.info(f"Login successful for user: {user.email} (ID: {user.id})")
    # Return user data (will be used by frontend Passport to establish session)
    return user # FastAPI converts SQLAlchemy User -> Pydantic UserRead
@app.on_event("startup")
async def startup_event():
    logger.info("Running backend startup event...")
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        logger.info(f"Data storage directory '{os.path.abspath(DATA_DIR)}' ensured.")
    except OSError as e:
        logger.error(f"Could not create data storage directory '{DATA_DIR}' at startup: {e}")
    if engine:
        async with engine.begin() as conn:
            try:
                logger.info("Attempting DB table creation/check...")
                # Import Base and User model HERE inside startup to ensure they are loa
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all) # Create tables based on Base
                logger.info("Database tables checked/created.")
            except Exception as e:
                logger.error(f"Error creating database tables: {e}", exc_info=True)
    else: logger.error("DB engine not initialized.")
@app.post(f"{API_V1_STR}/contact", response_model=ContactSubmitResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Contact & Track"])
async def endpoint_submit_contact_form(form_data: ContactFormInput):
    logger.info(f"POST {API_V1_STR}/contact received from {form_data.email}")
    if not all([form_data.name, form_data.email, form_data.subject, form_data.message]): raise HTTPException(400, "Missing required fields.")
    request_id = f"REQ-{str(uuid.uuid4())[:8].upper()}"; status_text = "Received"; timestamp = datetime.datetime.now()
    request_data = {"request_id": request_id, "timestamp": timestamp, "status": status_text, **form_data.model_dump()}
    try:
        request_store.append(request_data) # Store in memory for tracking
        logger.info(f"Contact Request {request_id} stored in memory.")
        contact_fieldnames = ["request_id", "timestamp", "status", "name", "email", "company", "phone", "subject", "message"]
        if not save_to_csv(CONTACTS_FILE, contact_fieldnames, request_data): raise RuntimeError("Failed to save contact to CSV")
        return ContactSubmitResponse(message="Inquiry received! Your request ID:", request_id=request_id, status=status_text)
    except Exception as e: logger.error(f"Error processing contact {form_data.email}: {e}", exc_info=True); raise HTTPException(500, "Server error processing contact.")

@app.get(f"{API_V1_STR}/track", response_model=TrackingResponse, status_code=status.HTTP_200_OK, tags=["Contact & Track"])
async def endpoint_track_requests(identifier: str = Query(..., min_length=3, description="Email or Phone")):
    logger.info(f"GET {API_V1_STR}/track received for identifier: {identifier}")
    matching_requests: List[TrackedRequest] = []
    try: # Query IN-MEMORY list (Replace with DB)
        for req in request_store:
            if (req.get('email') and req['email'].lower() == identifier.lower()) or \
               (req.get('phone') and req['phone'] == identifier):
                matching_requests.append(TrackedRequest(request_id=req.get("request_id"), timestamp=req.get("timestamp"), status=req.get("status"), subject=req.get("subject")))
        return TrackingResponse(identifier=identifier, requests=matching_requests)
    except Exception as e: logger.error(f"Error tracking: {e}", exc_info=True); raise HTTPException(500, "Error tracking requests.")
# --- Update this function in backend/main.py or ai_service.py ---
# --- Add/Update these helpers in backend/main.py ---
# Ensure pandas, io, traceback, docx (conditional) are imported

MAX_EXCERPT_CHARS = 8000 # Total chars for excerpt (e.g., 4k start, 4k end)
CHARS_PER_CHUNK = 4000  # Approx chars for start/end chunks

def create_file_excerpt(full_text: str, max_len: int = MAX_EXCERPT_CHARS) -> str:
    """Creates an excerpt from the beginning and end of the text."""
    if len(full_text) <= max_len:
        return full_text # Return full text if already short enough

    start_chunk = full_text[:CHARS_PER_CHUNK].strip()
    end_chunk = full_text[-CHARS_PER_CHUNK:].strip()

    excerpt = (
        f"[EXCERPT START]\n{start_chunk}\n...\n"
        f"[CONTENT TRUNCATED - ONLY START AND END SHOWN]\n...\n"
        f"{end_chunk}\n[EXCERPT END]"
    )
    return excerpt

async def start_new_conversation(db: AsyncSession, *, user_id: int, service_name: str) -> Conversation:
    """Creates a new conversation record in the database."""
    logger.info(f"Starting new conversation for user_id={user_id}, service={service_name}")
    new_conv = Conversation(user_id=user_id, service_name=service_name)
    db.add(new_conv)
    await db.flush() # Flush to get ID before commit (needed for returning)
    await db.refresh(new_conv) # Refresh to load defaults
    logger.info(f"New conversation created with ID: {new_conv.id}")
    # Commit happens via get_db dependency's context manager
    return new_conv
def compress_text(text: str) -> bytes:
    """Compresses text using zlib."""
    try:
        # Encode to bytes before compressing
        return zlib.compress(text.encode('utf-8',errors='replace'))
    except Exception as e:
        logger.error(f"Error compressing text: {e}", exc_info=True)
        # Fallback: return original text encoded if compression fails? Or raise?
        # Returning encoded original might exceed DB column size if it was large
        # Best to raise or return indicator of failure. Let's raise for now.
        raise ValueError(f"Compression failed: {e}")
        return b''

def decompress_text(data: bytes) -> str:
    """Decompresses text using zlib."""
    try:
        # Decompress bytes and decode back to string
        return zlib.decompress(data).decode('utf-8',errors='replace')
    except zlib.error as e:
         logger.error(f"Zlib decompression error: {e}", exc_info=False)
         return "[Error: Could not decompress message]"
    except UnicodeDecodeError as e:
         logger.error(f"UTF-8 decode error after decompression: {e}", exc_info=True)
         # Try latin-1 as fallback? Or return error string?
         try:
            return zlib.decompress(data).decode('latin-1', errors='ignore')
         except Exception:
             return "[Error: Could not decode decompressed message]"
    except Exception as e:
        logger.error(f"Unexpected error decompressing text: {e}", exc_info=True)
        return f"[Error: Decompression failed ({type(e).__name__})]"
async def add_message(db: AsyncSession, *, conv_id: int, role: str, content: str) -> Message:
    """Adds a new message to a conversation, compressing content."""
    logger.debug(f"Adding message to conv_id={conv_id}, role={role}")
    if role not in ["user", "model"]: # Basic validation
        raise ValueError("Role must be 'user' or 'model'")
    compressed_content = compress_text(content) # Compress before saving
    if not compressed_content:
         logger.error(f"Message content for conv {conv_id} could not be compressed. Storing empty.")
         # Decide: Skip saving? Save empty? Return None?
         # Let's save empty for now, but returning None might be better
         # return None
         compressed_content = b'' # Store empty bytes if compression failed

    new_msg = Message(
        conversation_id=conv_id,
        role=role,
        content=compressed_content # Save potentially empty bytes
    )
    db.add(new_msg)
    await db.flush()
    await db.refresh(new_msg)
    logger.debug(f"Message add attempted for conv {conv_id}. DB ID: {new_msg.id}")
    return new_msg

async def get_conversation_history(db: AsyncSession, *, conv_id: int, limit: int = 20) -> List[Dict[str, str]]:
    """Retrieves recent messages for a conversation, decompresses content."""
    logger.info(f"Retrieving history for conv_id={conv_id}, limit={limit}")
    statement = (
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.desc()) # Get latest first
        .limit(limit)
        # Use options for relationships if needed, but lazy='selectin' on model should work
        # .options(selectinload(Message.conversation)) # If you need conv info too
    )
    result = await db.execute(statement)
    db_messages = result.scalars().all()

    # Format history for AI (usually requires role/content dicts), decompressing
    # And reverse order to be chronological (oldest first)
    history_for_ai = []
    for msg in reversed(db_messages): # Reverse to get chronological order
        try:
            decompressed_content = decompress_text(msg.content)
            history_for_ai.append({"role": msg.role, "content": decompressed_content})
        except Exception as e:
            logger.error(f"Failed to decompress message ID {msg.id} for conv {conv_id}: {e}")
            history_for_ai.append({"role": msg.role, "content": "[Error: Message unreadable]"})

    logger.info(f"Retrieved {len(history_for_ai)} messages for conv_id={conv_id}")
    return history_for_ai
async def parse_uploaded_file_robust(file: UploadFile) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses uploaded file robustly, returns (excerpt, error_message).
    Supports txt, csv, xlsx, docx.
    """
    filename = file.filename.lower() if file.filename else "unknown_file"
    content_type = file.content_type
    full_text_content = None
    error_message = None

    logger.info(f"Attempting robust parse for: {filename}, Type: {content_type}")

    try:
        file_content_bytes = await file.read()
        # Ensure file pointer is reset if needed elsewhere, though BytesIO avoids this issue
        # await file.seek(0)

        if not file_content_bytes:
            logger.warning(f"File is empty: {filename}")
            return "[File is empty]", None

        if filename.endswith(".txt"):
            try:
                full_text_content = file_content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(f"UTF-8 decode failed for {filename}, trying latin-1.")
                full_text_content = file_content_bytes.decode('latin-1', errors='ignore')
            logger.info("Parsed TXT file.")

        elif filename.endswith(".csv") and ('text/csv' in content_type or '.csv' in filename):
             if pd:
                 file_like_object = io.BytesIO(file_content_bytes)
                 df = pd.read_csv(file_like_object)
                 # Include column names and limited rows in the text representation
                 buffer = io.StringIO()
                 buffer.write(f"CSV Columns: {', '.join(df.columns)}\n\n")
                 df.info(buf=buffer) # Include data types and non-null counts
                 buffer.write("\n--- Data Excerpt ---\n")
                 buffer.write(df.head(20).to_string(index=False)) # Show head
                 if len(df) > 40: buffer.write("\n...\n")
                 if len(df) > 20: buffer.write(df.tail(20).to_string(index=False)) # Show tail if long
                 full_text_content = buffer.getvalue()
                 logger.info(f"Parsed CSV file. Shape: {df.shape}")
             else: error_message = "Processing library (pandas) not available for CSV."

        elif filename.endswith((".xlsx", ".xls")) and ('spreadsheetml' in content_type or 'excel' in content_type or '.xls' in filename):
            if pd and openpyxl:
                file_like_object = io.BytesIO(file_content_bytes)
                # Consider reading only the first sheet, or add logic to iterate/select
                df = pd.read_excel(file_like_object, engine='openpyxl', sheet_name=0)
                buffer = io.StringIO()
                buffer.write(f"Excel Sheet (First) Columns: {', '.join(df.columns)}\n\n")
                df.info(buf=buffer)
                buffer.write("\n--- Data Excerpt ---\n")
                buffer.write(df.head(20).to_string(index=False))
                if len(df) > 40: buffer.write("\n...\n")
                if len(df) > 20: buffer.write(df.tail(20).to_string(index=False))
                full_text_content = buffer.getvalue()
                logger.info(f"Parsed XLSX/XLS file (first sheet). Shape: {df.shape}")
            else: error_message = "Processing library (pandas/openpyxl) not available for Excel."

        elif filename.endswith(".docx") and ('officedocument.wordprocessingml' in content_type or '.docx' in filename):
            if DOCX_LIB_AVAILABLE and docx:
                try:
                    file_like_object = io.BytesIO(file_content_bytes)
                    doc = docx.Document(file_like_object)
                    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                    # Basic table extraction (might need improvement)
                    table_texts = []
                    for table in doc.tables:
                         table_texts.append("\n--- Table Start ---")
                         for row in table.rows:
                              row_text = " | ".join(cell.text.strip() for cell in row.cells)
                              table_texts.append(row_text)
                         table_texts.append("--- Table End ---")

                    full_text_content = "\n".join(paragraphs + table_texts)
                    logger.info(f"Parsed DOCX file. Paragraphs: {len(paragraphs)}, Tables: {len(doc.tables)}")
                except Exception as docx_err: # Catch errors from python-docx itself
                    logger.error(f"python-docx failed to parse {filename}: {docx_err}", exc_info=True)
                    error_message = f"Failed to read DOCX content: {docx_err}"
            else: error_message = "Processing library (python-docx) not available for DOCX."

        else:
            error_message = f"Unsupported file type: {filename} ({content_type})"
            logger.warning(error_message)

        if error_message:
            return None, error_message

        if full_text_content:
            excerpt = create_file_excerpt(full_text_content, MAX_EXCERPT_CHARS)
            return excerpt, None
        else:
            # Should ideally be caught earlier or indicate empty content
            return "[File parsed but no text content extracted]", None

    except Exception as e:
        logger.error(f"Generic error parsing file {filename}: {traceback.format_exc()}")
        error_message = f"Unexpected error processing file: {e}"
        return None, error_message

# Precache service descriptions during startup
service_context_cache = {}

@app.on_event("startup")
async def cache_service_contexts():
    for package in custom_consulting_packages:
        service_context_cache[package['name']] = {
            'name': package['name'],
            'description': package['description']
        }

# Optimized compression with level tuning
def compress_text(text: str) -> bytes:
    return zlib.compress(text.encode('utf-8'), level=zlib.Z_BEST_SPEED)

# Streamlined prompt construction
SYSTEM_INSTRUCTION_TEMPLATE = """You are an expert AI assistant simulating a senior consultant at ZAlpha. Your current area of expertise is **'{service_name}'**.
Service Description: {service_description}
Analyze the ongoing conversation and the latest user query to provide helpful, insightful, relevant answers within the service context."""

DISCLAIMER = "\n\nDisclaimer: AI responses are informational and based on provided context/excerpts. Consult human experts for critical decisions."

async def get_contextual_ai_response(service_context: dict, user_query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    # Cache lookup optimization
    cached_context = service_context_cache.get(service_context['name'], {})
    system_instruction = SYSTEM_INSTRUCTION_TEMPLATE.format(
        service_name=cached_context.get('name', 'Unknown Service'),
        service_description=cached_context.get('description', '')
    )
    
    # Efficient history formatting
    formatted_history = [{'role': msg.get('role', 'user'), 'parts': [msg.get('content','')]} 
                        for msg in conversation_history if msg.get('content')]
    
    # Batch processing for large histories
    if len(formatted_history) > 10:
        formatted_history = formatted_history[-10:]  # Keep last 10 messages
    
    try:
        chat = ai_model.start_chat(history=formatted_history)
        response = await chat.send_message_async(
            f"{system_instruction}\n\n**User Query:** {user_query}"
        )
        return f"{response.text.strip()}{DISCLAIMER}"
    except Exception as e:
        logger.error(f"AI Error: {str(e)}")
        return f"Error: {str(e)}"

@app.post(f"{API_V1_STR}/hire", response_model=HireSubmitResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Hire"])
async def endpoint_submit_hire_request(form_data: HireConsultantForm):
    logger.info(f"POST {API_V1_STR}/hire received from {form_data.contact_email}")
    if not all([form_data.contact_name, form_data.contact_email, form_data.industry, form_data.business_function, form_data.project_timeline, form_data.work_type, form_data.project_description]):
        raise HTTPException(400, "Missing required hire request fields.")
    hire_request_id = f"HIRE-{str(uuid.uuid4())[:8].upper()}"; status_text = "Hire Request Received"; timestamp = datetime.datetime.now()
    hire_data = {"hire_request_id": hire_request_id, "timestamp": timestamp, "status": status_text, **form_data.model_dump()}
    try:
        # Save hire request to CSV (WARNING: Ephemeral)
        hire_fieldnames = ["hire_request_id", "timestamp", "status", "contact_name", "contact_email", "contact_phone", "contact_company", "industry", "business_function", "services_needed", "project_timeline", "start_date", "resources_required", "location", "work_type", "experience_needed", "skills_needed", "project_description"]
        save_data = hire_data.copy(); save_data["services_needed"] = ", ".join(form_data.services_needed) if form_data.services_needed else ""; save_data["start_date"] = form_data.start_date.isoformat() if form_data.start_date else ""
        if not save_to_csv(HIRE_REQUESTS_FILE, hire_fieldnames, save_data): raise RuntimeError("Failed to save hire request to CSV")
        return HireSubmitResponse(message="Hire request submitted! We will review.", hire_request_id=hire_request_id, status=status_text)
    except Exception as e: logger.error(f"Error processing hire request {form_data.contact_email}: {e}", exc_info=True); raise HTTPException(500, "Server error processing hire request.")

# UPDATED Startup Analysis Endpoint
@app.post(f"{API_V1_STR}/analyze/startup", response_model=StartupAnalysisResult, status_code=status.HTTP_200_OK, tags=["Analysis"])
async def endpoint_analyze_startup(info: StartupInput):
    logger.info(f"POST {API_V1_STR}/analyze/startup received for: {info.company_name}")
    try:
        analysis_result_text = await get_startup_analysis(info) # Call updated helper
        if analysis_result_text.startswith("Error:"):
            logger.warning(f"Startup analysis failed: {analysis_result_text}")
            # Return 200 OK but with error message in body
            return StartupAnalysisResult(analysis_text=None, error_message=analysis_result_text, disclaimer="Analysis failed.")
        logger.info(f"Startup analysis successful for {info.company_name}.")
        return StartupAnalysisResult(analysis_text=analysis_result_text, error_message=None)
    except Exception as e: logger.error(f"Error in startup analysis endpoint: {e}", exc_info=True); return StartupAnalysisResult(analysis_text=None, error_message=f"Unexpected server error: {e}", disclaimer="Analysis failed.")
# --- API Endpoints ---
API_V1_STR = "/api/v1"
router = APIRouter(prefix=API_V1_STR, tags=["APIv1"])


@app.post(
    f"{API_V1_STR}/ai-tool",
    response_model=AiChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Contextual AI Chat Assistant (with History)",
    description="Handles multi-turn conversations for a specific service.",
    tags=["Analysis"]
)
async def endpoint_ai_tool_chat(
    query_data: AiChatQuery,
    db: AsyncSession = Depends(get_db)
    # TODO: Add real user_id logic
):
    # Placeholder user_id
    user_id = 1
    logger.info(f"POST /ai-tool chat request for service: {query_data.service_name}, Conv ID: {query_data.conversation_id}, User ID: {user_id}")

    conversation_id = query_data.conversation_id
    history_for_ai = []

    try:
        # --- 1. Get or Start Conversation (DB Logic Placeholder) ---
        if conversation_id:
            history_for_ai = await get_conversation_history(db, conv_id=conversation_id)
            logger.info(f"Attempting to continue conversation ID: {conversation_id}")
            # Add actual DB fetch here
        else:
            new_conv = await start_new_conversation(db, user_id=user_id, service_name=query_data.service_name)
            conversation_id = new_conv.id
            logger.info("Starting new conversation (DB op skipped in example).")
            # Placeholder ID if no DB interaction yet for starting conv:
            if not conversation_id: conversation_id = 0 # Need a valid ID for add_message below if not using DB

        # --- 2. Add User Message to DB (DB Logic Placeholder) ---
        #await add_message(db, conv_id=conversation_id, role="user", content=query_data.user_query)


        # --- >>> 3. Prepare ACTUAL Service Context <<< ---
        service_name = query_data.service_name
        service_desc = "Description not found for this service." # Default
        # Find the matching package description from your static data
        # Ensure 'custom_consulting_packages' list is defined globally above
        package_data = next((pkg for pkg in custom_consulting_packages if pkg.get("name") == service_name), None)
        if package_data and package_data.get("description"):
            service_desc = package_data["description"]
            logger.info(f"Found description for service '{service_name}'")
        else:
             logger.warning(f"Could not find description for service '{service_name}' in static data.")

        # Create the context dictionary with the REAL description
        service_context = {"name": service_name, "description": service_desc}
        # --- >>> END Context Preparation <<< ---


        # 4. Call AI Service with History & CORRECT Context
        ai_response_text = await get_contextual_ai_response(
            service_context=service_context, # Pass the correct context
            user_query=query_data.user_query,
            conversation_history=history_for_ai # Pass history (currently empty placeholder)
        )

        # 5. Check for AI Errors
        if ai_response_text.startswith("Error:"):
             logger.warning(f"AI Tool processing issue: {ai_response_text}")
             return AiChatResponse(ai_response="AI failed to respond.", conversation_id=conversation_id or 0, error_message=ai_response_text)

        # 6. Add AI Message to DB (DB Logic Placeholder)
        #await add_message(db, conv_id=conversation_id, role="model", content=ai_response_text)

        # 7. Return AI response and conversation ID
        # If conversation_id is still 0 (placeholder), the frontend should handle it
        return AiChatResponse(ai_response=ai_response_text, conversation_id=conversation_id or 0)

    except HTTPException: raise
    except Exception as e:
        logger.error(f"Error in /ai-tool chat endpoint: {e}", exc_info=True)
        return AiChatResponse(ai_response="Server error.", conversation_id=conversation_id or 0, error_message=f"Server error: {e}")

# --- Keep other endpoint definitions ---
# --- Keep other endpoint definitions ---
Prompt_Suggestions = {
    "Technology Due Diligence": [
        "Assess the scalability of the target company's main product.",
        "What are the major technical risks in this architecture?",
        "Evaluate the quality of the codebase based on this description...",
        "How efficient is their DevOps process?",
        "Summarize the key findings from the attached technical report."
    ],
    "Commercial Due Diligence (CDD)": [
        "Analyze the target market size and growth potential.",
        "What are the key differentiators against competitors?",
        "Summarize customer feedback analysis.",
        "Assess the realism of the revenue projections.",
        "Evaluate the management team's strengths for executing the strategy."
    ],
    "Go To Market Strategy": [
        "Suggest target customer segments for this new product.",
        "Propose effective marketing channels.",
        "Develop a framework for a pricing strategy.",
        "What KPIs should we track for this GTM plan?",
        "Analyze the competitive landscape for this launch."
    ],
    # Add suggestions for other service packages...
    "Default": [
        "Summarize the key points in the attached document.",
        "What are the main risks related to this service?",
        "Outline a typical process flow for this type of engagement.",
        "What are common challenges faced during this service?"
    ]
}

def get_prompt_suggestions(service_name: str) -> List[str]:
    """Returns relevant prompt suggestions for a given service name."""
    return PROMPT_SUGGESTIONS.get(service_name, PROMPT_SUGGESTIONS["Default"])
# --- NEW Prompt Suggestions Endpoint ---
@app.get(
    "/ai-prompt-suggestions",
    response_model=List[str], # Returns a list of strings
    status_code=status.HTTP_200_OK,
    summary="Get AI Prompt Suggestions",
    description="Provides example prompts relevant to a specific service package name.",
    tags=["Analysis"]
)
async def endpoint_get_ai_prompt_suggestions(service_name: str = Query(..., description="Name of the service package")):
    logger.info(f"GET /ai-prompt-suggestions for service: {service_name}")
    try:
        suggestions = get_prompt_suggestions(service_name)
        return suggestions
    except Exception as e:
        logger.error(f"Error fetching prompt suggestions for {service_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve suggestions.")
# ... Keep User Endpoints (/users/find-or-create, /users/{id}, /users/me) ...
# ... Keep Health Check ...
# --- Root Endpoint (Health Check) ---
# This is defined correctly on the app instance
@app.get("/")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

# --- Uvicorn Run Command (for reference) ---
# If saving this as backend/main.py, run from project root:
# uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --env-file backend/.env
# If saving as main.py directly in backend/, run from backend/:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000 --env-file .env
