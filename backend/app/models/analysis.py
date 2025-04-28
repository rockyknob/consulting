# --- backend/app/models/analysis.py (Corrected) ---
# Updated: Tuesday, April 22, 2025 at 11:45 PM IST (New Delhi)

from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import List, Dict, Any, Optional
import datetime # Import datetime for TrackedRequest

# --- P&L Analysis Models (Keep as before) ---
class PnlInputData(BaseModel):
    revenue: Optional[float] = None; cogs: Optional[float] = None; gross_profit: Optional[float] = None
    operating_expenses: Optional[Dict[str, float]] = None; operating_income: Optional[float] = None
    interest_expense: Optional[float] = None; taxes: Optional[float] = None
    net_income: Optional[float] = None; period: Optional[str] = None

class PnlRatios(BaseModel):
    gross_margin_percent: Optional[float] = None
    operating_margin_percent: Optional[float] = None
    net_margin_percent: Optional[float] = None

class PnlAnalysisResult(BaseModel):
    filename: str
    processing_status: str = "Completed"
    extracted_data: Optional[PnlInputData] = None
    calculated_ratios: Optional[PnlRatios] = None
    ai_insights: Optional[str] = None
    ai_swot_analysis: Optional[str] = None # Kept from previous structure
    disclaimer: str = "Default disclaimer: Verify results." # Provide default
    error_message: Optional[str] = None

# --- Startup Analysis Models (Corrected) ---
class StartupInfoInput(BaseModel): # Renamed for clarity from HireConsultantForm if mixed before
    # Basic Info
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

class IndustryIntel(BaseModel):
    """Represents a piece of fetched industry intelligence."""
    title: str
    link: Optional[HttpUrl] = None # Use HttpUrl for validation
    source: Optional[str] = None # e.g., "Forbes", "Gartner", "TechCrunch"
    snippet: Optional[str] = None
    type: str # 'report', 'news', 'deal'

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


# --- AI Tool Models (Keep as before) ---
class AiToolQuery(BaseModel):
    user_query: str = Field(..., min_length=5, max_length=1500)
    service_context: Dict[str, Any] = Field(...)

class AiToolResponse(BaseModel):
    ai_response: str
    error_message: Optional[str] = None
    # Disclaimer is part of the AI response text based on prompt

# --- Contact & Tracking Models (Assuming these are needed by endpoints.py) ---
# Copied from main.py single-file version for completeness if using structured approach
class ContactFormInput(BaseModel): # If used by contact endpoint
    name: str; email: EmailStr; company: Optional[str] = None; phone: Optional[str] = None; subject: str; message: str

class ContactSubmitResponse(BaseModel): # If used by contact endpoint
    message: str; request_id: str; status: str

class TrackedRequest(BaseModel): # If used by track endpoint
    request_id: str; timestamp: datetime.datetime; status: str; subject: str

class TrackingResponse(BaseModel): # If used by track endpoint
    identifier: str; requests: List[TrackedRequest]

class HireConsultantForm(BaseModel): # If used by hire endpoint
    contact_name: str = Field(...); contact_email: EmailStr; contact_phone: Optional[str] = None; contact_company: Optional[str] = None; industry: str = Field(...); business_function: str = Field(...); services_needed: List[str] = Field([]); project_timeline: str = Field(...); start_date: Optional[datetime.date] = None; resources_required: Optional[str] = None; location: Optional[str] = None; work_type: str = Field(...); experience_needed: Optional[str] = None; skills_needed: Optional[str] = None; project_description: str = Field(..., min_length=10)

class HireSubmitResponse(BaseModel): # If used by hire endpoint
    message: str; hire_request_id: str; status: str