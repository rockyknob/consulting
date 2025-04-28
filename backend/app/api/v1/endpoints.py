# --- backend/app/api/v1/endpoints.py ---

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
# Import models using alias
from app.models import analysis as analysis_models
from app.models import contact as contact_models
from app.models import user as user_models # <<< --- ADD THIS LINE --- >>>
# Import services
from app.services.analysis_service import analysis_svc_instance
# from app.services import email_service # Uncomment if used
from app.services import user_service # Ensure user service is imported if used
# Import static data
from app.services.static_data import (services_data, clients_data, testimonials_data, hero_content, products_data, custom_consulting_packages)
# Import DB dependency
from app.db.database import get_db
# Import standard libraries
import datetime
import logging
import uuid
import csv
import os
from typing import List, Dict, Any
import pandas as pd
import io
import traceback
# Import docx conditionally based on install check
if DOCX_LIB_AVAILABLE:
    import docx # Should be import docx# Added for CSV helper

logger = logging.getLogger(__name__)
router = APIRouter() # Create router instance
router = APIRouter()
# --- !!! TEMPORARY IN-MEMORY STORE - REPLACE WITH DATABASE !!! ---
request_store: List[Dict[str, Any]] = []
# -------------------------------------------------------------------

# --- !!! TEMPORARY CSV HELPER - MOVE TO SERVICE/UTIL MODULE !!! ---
DATA_DIR = os.path.join("backend", "data_storage") # Relative to project root
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.csv")
HIRE_REQUESTS_FILE = os.path.join(DATA_DIR, "hire_requests.csv")

def save_to_csv(filepath: str, fieldnames: List[str], row_data: Dict[str, Any]):
    """Generic helper to append a row to a CSV file. Returns True on success."""
    # Ensure directory exists before writing
    dir_name = os.path.dirname(filepath)
    if dir_name: # Check if path includes a directory
        try:
            os.makedirs(dir_name, exist_ok=True)
        except OSError as e:
            logger.error(f"Could not ensure data storage directory '{dir_name}': {e}")
            return False # Cannot save if directory fails

    file_exists = os.path.isfile(filepath)
    try:
        with open(filepath, mode='a', newline='', encoding='utf-8') as csvfile:
            # Use extrasaction='ignore' in case row_data has extra keys not in fieldnames
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            if not file_exists or os.path.getsize(filepath) == 0:
                writer.writeheader()
            # Prepare row data specifically for the defined fieldnames
            csv_row = {field: str(row_data.get(field, "")).replace('\n', '\\n') for field in fieldnames}
            writer.writerow(csv_row)
        logger.info(f"Data successfully saved to {os.path.basename(filepath)}")
        return True
    except IOError as e:
        logger.error(f"IOError writing CSV {filepath}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error writing CSV {filepath}: {e}", exc_info=True)
    return False # Indicate failure
# --- END TEMPORARY CSV HELPER ---


# --- Static Content Endpoint ---
@router.get(
    "/content",
    status_code=status.HTTP_200_OK,
    summary="Get Static Website Content",
    description="Returns predefined content for hero, services, products, clients, testimonials sections."
)
async def get_website_content_route():
    logger.info(f"Request received for /content")
    try:
        # Data is imported directly from static_data.py now
        content = {
            "hero": hero_content,
            "services": services_data,
            "clients": clients_data,
            "testimonials": testimonials_data,
            "products": products_data,
            "custom_consulting_packages": custom_consulting_packages,
            "current_year": datetime.datetime.now().year
        }
        return content
    except Exception as e:
        logger.error(f"Error fetching static content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load website content.")

# --- Contact Form Endpoint ---
@router.post(
    "/contact",
    response_model=contact_models.ContactSubmitResponse, # Use the correct response model
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Contact Form",
    description="Accepts contact form data, saves to CSV (ephemeral), adds to in-memory store for tracking."
)
async def post_contact_form(form_data: contact_models.ContactFormInput): # Use Input model
    logger.info(f"Received contact form submission from {form_data.email}")
    if not all([form_data.name, form_data.email, form_data.subject, form_data.message]):
        raise HTTPException(status_code=400, detail="Missing required contact fields.")

    request_id = f"REQ-{str(uuid.uuid4())[:8].upper()}"
    status_text = "Received" # Use consistent status text
    timestamp = datetime.datetime.now()

    # Prepare data for storage/tracking
    request_data = {
        "request_id": request_id,
        "timestamp": timestamp,
        "status": status_text,
        "name": form_data.name, # Get fields from input model
        "email": str(form_data.email),
        "company": form_data.company,
        "phone": form_data.phone,
        "subject": form_data.subject,
        "message": form_data.message,
    }

    try:
        # Store in memory for tracking (TEMPORARY)
        request_store.append(request_data)
        logger.info(f"Contact Request {request_id} stored in memory. Store size: {len(request_store)}")

        # Save to CSV (WARNING: EPHEMERAL ON FREE HOSTING - REPLACE WITH DB)
        contact_fieldnames = ["request_id", "timestamp", "status", "name", "email", "company", "phone", "subject", "message"]
        if not save_to_csv(CONTACTS_FILE, contact_fieldnames, request_data):
            # If saving fails, log critical error but maybe still return success? Or fail request?
            # Let's make CSV save failure a server error for now.
            logger.error(f"CRITICAL: Failed to save contact request {request_id} to CSV.")
            raise HTTPException(status_code=500, detail="Failed to record inquiry due to server error.")

        # Optional: Trigger email sending via email_service if implemented
        # try:
        #     await email_service.send_contact_email(form_data)
        # except Exception as email_error:
        #     logger.error(f"Contact email failed for {request_id}: {email_error}", exc_info=True)
            # Don't fail the whole request if only email fails

        # Return success response including ID and Status
        return contact_models.ContactSubmitResponse(
            message="Inquiry received! Your request ID is provided below.",
            request_id=request_id,
            status=status_text
        )

    except HTTPException:
         raise # Re-raise validation errors etc.
    except Exception as e:
        logger.error(f"Unexpected error processing contact form {form_data.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error processing contact request.")


# --- Request Tracking Endpoint ---
@router.get(
    "/track",
    response_model=contact_models.TrackingResponse, # Use correct response model
    status_code=status.HTTP_200_OK,
    summary="Track Contact Request Status",
    description="Retrieves status of contact requests matching identifier from IN-MEMORY store (lost on restart)."
)
async def get_track_requests(identifier: str = Query(..., min_length=3, description="Email or Phone used in submission")):
    logger.info(f"GET /track received for identifier: {identifier}")
    matching_requests: List[contact_models.TrackedRequest] = [] # Use model for list type
    try:
        # Query IN-MEMORY list (REPLACE WITH DB QUERY)
        for req in request_store: # Only searches contact requests currently
            match_email = req.get('email') and req['email'].lower() == identifier.lower()
            match_phone = req.get('phone') and req['phone'] == identifier # Basic exact match
            if match_email or match_phone:
                matching_requests.append(contact_models.TrackedRequest(
                    request_id=req.get("request_id", "N/A"),
                    timestamp=req.get("timestamp", datetime.datetime.min),
                    status=req.get("status", "Unknown"),
                    subject=req.get("subject", "N/A")
                ))
        logger.info(f"Found {len(matching_requests)} requests for identifier: {identifier}")
        return contact_models.TrackingResponse(identifier=identifier, requests=matching_requests)
    except Exception as e:
        logger.error(f"Error tracking requests for {identifier}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error tracking requests.")


# --- Hire Request Endpoint ---
@router.post(
    "/hire",
    response_model=contact_models.HireSubmitResponse, # Use correct response model
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Hire Request Form",
    description="Accepts hire request details and saves to CSV (ephemeral)."
    )
async def post_hire_request(form_data: contact_models.HireConsultantForm): # Use correct input model
    logger.info(f"POST /hire received from {form_data.contact_email}")
    # Pydantic validation done. Add app-level validation if needed.
    if not all([form_data.contact_name, form_data.contact_email, form_data.industry, form_data.business_function, form_data.project_timeline, form_data.work_type, form_data.project_description]):
        raise HTTPException(status_code=400, detail="Missing required hire request fields.")

    hire_request_id = f"HIRE-{str(uuid.uuid4())[:8].upper()}"
    status_text = "Hire Request Received"
    timestamp = datetime.datetime.now()

    hire_data = {
        "hire_request_id": hire_request_id, "timestamp": timestamp, "status": status_text,
        **form_data.model_dump() # Get data from Pydantic model
    }

    try:
        # Save hire request to CSV (WARNING: Ephemeral on free hosting)
        hire_fieldnames = [ # Match HireConsultantForm fields + meta fields
            "hire_request_id", "timestamp", "status", "contact_name", "contact_email",
            "contact_phone", "contact_company", "industry", "business_function",
            "services_needed", "project_timeline", "start_date", "resources_required",
            "location", "work_type", "experience_needed", "skills_needed", "project_description"
        ]
        # Prepare data for CSV saving helper (flatten list, format date)
        save_data = hire_data.copy()
        save_data["services_needed"] = ", ".join(form_data.services_needed) if form_data.services_needed else ""
        save_data["start_date"] = form_data.start_date.isoformat() if form_data.start_date else ""

        if not save_to_csv(HIRE_REQUESTS_FILE, hire_fieldnames, save_data):
            # Make save failure critical
            logger.error(f"CRITICAL: Failed to save hire request {hire_request_id} to CSV.")
            raise RuntimeError("Failed to save hire request due to storage issue.")

        # Optionally add to in-memory store too if needed for immediate ops/tracking?
        # hire_request_store.append(hire_data)

        return contact_models.HireSubmitResponse(
            message="Hire request submitted successfully! We will review and contact you.",
            hire_request_id=hire_request_id,
            status=status_text
            )

    except HTTPException: raise # Re-raise validation errors etc.
    except RuntimeError as storage_error:
         logger.error(f"Failed to process/save hire request data: {storage_error}", exc_info=True)
         raise HTTPException(status_code=500, detail="Server error processing hire request.")
    except Exception as e:
         logger.error(f"Unexpected error processing hire request {form_data.contact_email}: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail="Unexpected server error processing hire request.")


# --- P&L Analysis Endpoint Placeholder ---
# Keep the endpoint defined, but use the service instance which might handle errors gracefully
@router.post(
    "/analyze/pnl",
    response_model=analysis_models.PnlAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze Financial Statement (Experimental)",
    description="Upload file (.xlsx, .csv, .txt, .docx). Attempts parsing & AI analysis. Reliability varies."
)
async def post_analyze_pnl( file: UploadFile = File(...) ):
    logger.info(f"Received PNL analysis request via API for file: {file.filename}")
    allowed_extensions = ('.xlsx', '.csv', '.txt', '.docx')
    if not file.filename or not file.filename.lower().endswith(allowed_extensions):
         raise HTTPException(status_code=400, detail=f"Invalid file type. Supported: {', '.join(allowed_extensions)}")
    try:
        # Assuming analysis_svc_instance exists and handles internal errors
        result = await analysis_svc_instance.analyze_pnl(file) # Defined in analysis_service.py
        if result.processing_status == "Error" and not result.error_message.startswith("Parsing failed"):
             # If it's an internal server error during analysis (not user input format)
             raise HTTPException(status_code=500, detail=result.error_message or "Analysis failed due to server error.")
        elif result.processing_status == "Error":
             # If it's a parsing error, return 400 but with the result body
             raise HTTPException(status_code=400, detail=result.error_message or "File parsing failed.")
        return result
    except HTTPException: raise
    except Exception as e: logger.error(f"Unhandled exception in /analyze/pnl endpoint: {e}", exc_info=True); raise HTTPException(500, "Unexpected server error during PNL analysis.")


# --- Startup Analysis Endpoint ---
@router.post(
    "/analyze/startup",
    response_model=analysis_models.StartupAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze Startup Information (AI)",
    description="Provide startup details for AI consultation, Berkus factor discussion, and trend insights."
)
async def endpoint_analyze_startup(info: analysis_models.StartupInfoInput): # Ensure model name matches
    logger.info(f"POST /analyze/startup received for: {info.company_name} in industry: {info.industry}")
    current_year = datetime.datetime.now().year
    industry = info.industry # Get industry for search

    # --- 1. Perform Web Searches (Simulated - Requires Tool Call) ---
    reports: List[analysis_models.IndustryIntel] = []
    news: List[analysis_models.IndustryIntel] = []
    deals: List[analysis_models.IndustryIntel] = []
    search_error = None

    # --- >>> Placeholder for Search Tool Integration <<< ---
    # In a real implementation, you would call your search tool here
    # using queries based on the 'industry' variable.
    # Example (conceptual - actual tool call depends on your setup):
    # search_queries = [
    #     f"latest industry analysis report {industry} {current_year}",
    #     f"market trends {industry} {current_year}",
    #     f"{industry} industry news recent",
    #     f"{industry} funding deals OR M&A {current_year}"
    # ]
    # try:
    #     search_results = await perform_web_search(search_queries) # Your search function
    #     # Process search_results: Filter, categorize, limit number, create IndustryIntel objects
    #     reports = process_search_results(search_results, type='report', limit=2)
    #     news = process_search_results(search_results, type='news', limit=4)
    #     deals = process_search_results(search_results, type='deal', limit=3)
    # except Exception as e:
    #     logger.error(f"Web search failed for industry {industry}: {e}")
    #     search_error = "Could not retrieve latest industry intelligence."
    # --- >>> End Placeholder <<< ---

    # Using dummy data for demonstration since search tool call isn't performed here:
    logger.warning("Using dummy data for industry intelligence - Web search not implemented in this example.")
    if industry.lower() == "saas": # Example dummy data
         news = [analysis_models.IndustryIntel(title="AI Integration Boosts SaaS Valuations", link="https://example.com/news1", source="TechNews", type="news"), analysis_models.IndustryIntel(title="Vertical SaaS Sees Record Growth", link="https://example.com/news2", source="Industry Times", type="news")]
         reports = [analysis_models.IndustryIntel(title=f"State of SaaS {current_year} Report", link="https://example.com/report1", source="Gartner", type="report")]
         deals = [analysis_models.IndustryIntel(title="Acme SaaS raises $50M Series B", link="https://example.com/deal1", source="VC Crunch", type="deal")]
    else:
         news = [analysis_models.IndustryIntel(title="General Tech News Example", link="https://example.com/gnews", source="Generic Source", type="news")]


    # --- 2. Get AI Text Analysis (Using updated function) ---
    ai_analysis_text = None
    ai_error = None
    try:
        # Assuming get_startup_analysis is defined in ai_service module
        ai_analysis_text = await ai_service.get_startup_analysis(info)
        if ai_analysis_text.startswith("Error:"):
            ai_error = ai_analysis_text # Capture specific AI error
            ai_analysis_text = None # Don't show error as main text
    except Exception as e:
        logger.error(f"Error calling get_startup_analysis: {e}", exc_info=True)
        ai_error = "Failed to generate AI analysis text."

    # --- 3. Construct Response ---
    final_error = ai_error or search_error # Prioritize AI error if both fail
    final_status = "Completed with errors" if final_error else "Completed"
    final_disclaimer = analysis_models.StartupAnalysisResult.__fields__["disclaimer"].default # Get default disclaimer

    # Include a specific notice if search failed but AI worked
    if search_error and not ai_error:
         final_disclaimer += f" | Notice: {search_error}"

    return analysis_models.StartupAnalysisResult(
        analysis_text=ai_analysis_text,
        industry_reports=reports if reports else None,
        latest_news=news if news else None,
        recent_deals=deals if deals else None,
        processing_status=final_status,
        error_message=final_error,
        disclaimer=final_disclaimer
    )

# --- AI Tool Endpoint ---
@router.post(
    "/ai-tool",
    response_model=analysis_models.AiToolResponse,
    status_code=status.HTTP_200_OK,
    summary="Contextual AI Assistant",
    description="Provides AI insights based on query within a selected service package context."
)
@app.post( # Or @router.post
    f"{API_V1_STR}/ai-tool",
    response_model=AiToolResponse, status_code=status.HTTP_200_OK,
    summary="Contextual AI Assistant with File Upload & Excerpting", tags=["Analysis"]
)
async def endpoint_ai_tool_query(
    user_query: str = Form(..., min_length=3), # Min length adjusted
    service_context_json: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    logger.info(f"POST /ai-tool. File: {file.filename if file else 'No'}")
    try:
        service_context = json.loads(service_context_json)
        if not isinstance(service_context, dict): raise ValueError("Invalid context")
    except Exception as e: raise HTTPException(400, f"Invalid service context: {e}")

    file_excerpt_text = None
    parsing_error = None
    if file:
        try:
            # Call the ROBUST parsing function
            file_excerpt_text, parsing_error = await parse_uploaded_file_robust(file)
            if parsing_error:
                 logger.warning(f"File parsing issue for {file.filename}: {parsing_error}")
                 # Decide how to handle: pass error message to AI? Return error directly?
                 # For now, we'll pass the error message string as the "excerpt"
                 file_excerpt_text = f"[File Parsing Error: {parsing_error}]"
        except Exception as e:
             logger.error(f"Critical error processing file {file.filename}: {e}", exc_info=True)
             file_excerpt_text = "[Critical error processing file]" # Inform AI
        finally: await file.close()

    # Call AI service with potentially parsed/error text
    try:
        ai_response_text = await get_contextual_ai_response(
            service_context=service_context,
            user_query=user_query,
            file_excerpt=file_excerpt_text # Pass excerpt or parsing error msg
        )
        if ai_response_text.startswith("Error:"):
            return AiToolResponse(ai_response="Could not generate AI response.", error_message=ai_response_text)
        return AiToolResponse(ai_response=ai_response_text)
    except Exception as e:
        logger.error(f"Error in /ai-tool endpoint logic: {e}", exc_info=True)
        raise HTTPException(500, "Server error during AI processing.")
@router.post(
    "/users/find-or-create",
    response_model=user_models.UserRead, # Return user details from DB
    status_code=status.HTTP_200_OK, # OK if found, Created implicitly handled by GET first
    summary="Find or Create User from OAuth",
    tags=["Users & Auth"],
    description="Called by frontend Passport callback. Finds user by provider ID or creates new user in DB."
)
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

# --- End File Parsing Utilities ---
async def find_or_create_user_endpoint(
    user_data: user_models.UserUpsertData, # Data sent by frontend Passport callback
    db: AsyncSession = Depends(get_db) # Inject DB session
):
    logger.info(f"Endpoint: /users/find-or-create called for provider={user_data.provider}")
    try:
        user = await user_service.get_or_create_user(db=db, user_data=user_data)
        if not user:
             # This case should ideally not happen if get_or_create works
             logger.error("User service failed to get or create user unexpectedly.")
             raise HTTPException(status_code=500, detail="Failed to process user login.")
        logger.info(f"Returning user data for ID: {user.id}")
        return user # FastAPI automatically converts SQLAlchemy model -> Pydantic UserRead
    except Exception as e:
        logger.error(f"Error in find_or_create_user_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error during user processing: {e}")


@router.get(
    "/users/{user_id}",
    response_model=user_models.UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get User By ID",
    description="Retrieves user details by internal database ID. (NOTE: Needs proper API authentication in production)."
)
async def get_user_by_id_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db)
    # --- Authentication Dependency Needed Here ---
    # current_api_user: user_models.UserRead = Depends(get_current_active_api_user) # Example
    # --- End Authentication Dependency ---
):
    # WARNING: This endpoint is currently INSECURE without proper authentication
    # Anyone could query any user ID. Add auth dependency (e.g., JWT check) later.
    logger.info(f"Endpoint: /users/{user_id} requested.") # (Insecure log, remove in prod)

    db_user = await user_service.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        logger.warning(f"User with ID {user_id} not found.")
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


# --- Conceptual /users/me endpoint ---
# This requires the API call itself to be authenticated (e.g., with a JWT)
# to know who "me" is. We defer implementing the auth dependency for now.
@router.get(
    "/users/me",
    response_model=user_models.UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Retrieves details for the currently authenticated API user. (NOTE: Requires API authentication like JWT to be implemented)."
)
async def read_users_me(
    # --- Authentication Dependency Needed Here ---
    # Example: Depends on a function that validates a JWT bearer token
    # current_api_user: user_models.UserRead = Depends(get_current_active_api_user)
    # --- End Authentication Dependency ---
    db: AsyncSession = Depends(get_db) # Keep DB dependency
):
    # raise HTTPException(status_code=501, detail="API Authentication for /users/me not implemented")
    # For now, just return a placeholder or the first user for testing (INSECURE)
    logger.warning("Accessing /users/me endpoint without proper API authentication!")
    # Replace this with logic using the authenticated user from the dependency
    # return current_api_user
    # ---- TEMPORARY/INSECURE Placeholder ----
    statement = select(UserModel).limit(1)
    result = await db.execute(statement)
    first_user = result.scalar_one_or_none()
    if not first_user: raise HTTPException(status_code=404, detail="No users found (placeholder)")
    return first_user


# --- Add these endpoints in main.py ---



# Keep existing endpoints: /content, /contact, /track, /hire, /analyze/startup, /ai-tool, /users/find-or-create, /users/{id}, /users/me
# Keep: get_user_by_provider_id, get_or_create_user (for OAuth), get_user_by_id
# ...
# --- Startup Event (Ensure directory exists) ---

    # Remove DB table creation logic if not using DB
    # async with engine.begin() as conn: ... await conn.run_sync(Base.metadata.create_all) ...


