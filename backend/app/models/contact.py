from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, List # Keep List if TrackedRequest/TrackingResponse are here
import datetime
class ContactFormInput(BaseModel):
    name: str
    email: EmailStr
    company: str | None = None
    phone: str | None = None
    subject: str
    message: str
    
class ContactSubmitResponse(BaseModel):
    message: str
    request_id: str
    status: str
class TrackedRequest(BaseModel):
    """Structure for displaying a single tracked request."""
    request_id: str
    timestamp: datetime.datetime
    status: str
    subject: str
    # Note: Avoid returning sensitive details like email/phone here

class TrackingResponse(BaseModel):
    """Structure for the response from the /track endpoint."""
    identifier: str # The email or phone used for searching
    requests: List[TrackedRequest] # A list of matching requests
class HireConsultantForm(BaseModel): # Input model for the /hire endpoint
    contact_name: str = Field(..., examples=["Jane Doe"])
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    contact_company: Optional[str] = None
    industry: str = Field(..., examples=["Technology"])
    business_function: str = Field(..., examples=["Strategy"])
    services_needed: List[str] = Field([], examples=[["tech_dd"]])
    project_timeline: str = Field(..., examples=["3-6 months"])
    start_date: Optional[datetime.date] = None
    resources_required: Optional[str] = None
    location: Optional[str] = None
    work_type: str = Field(..., examples=["Hybrid"])
    experience_needed: Optional[str] = None
    skills_needed: Optional[str] = None
    project_description: str = Field(..., min_length=10)

class HireSubmitResponse(BaseModel): # Response model for the /hire endpoint
    message: str
    hire_request_id: str
    status: str  