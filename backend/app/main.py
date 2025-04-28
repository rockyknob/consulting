# --- backend/main.py ---
# Single file implementation including all features.
# WARNING: Uses temporary in-memory storage for tracking and
# non-persistent CSV file saving for submissions on most free hosting.
# DATABASE INTEGRATION IS REQUIRED FOR PRODUCTION DEPLOYMENT.

import fastapi
from fastapi import FastAPI, HTTPException, status, Query, UploadFile, File, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import datetime
import os
import csv
import logging
from dotenv import load_dotenv
import uuid
from typing import List, Dict, Any, Optional
import traceback
import io
import pandas as pd
import re
# --- backend/app/main.py ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import endpoints as api_v1_endpoints # Import the main router
from app.db.base import Base # Import Base for table creation
from app.db.database import engine # Import engine for table creation
import logging
import os

logger = logging.getLogger(__name__)

# --- Database Table Creation (Basic - use Alembic for production) ---
# This function will run once when the application starts
@app.on_event("startup")
async def startup_event():
    logger.info("Running startup event...")
    async with engine.begin() as conn:
        try:
            logger.info("Attempting to create database tables...")
            # await conn.run_sync(Base.metadata.drop_all) # Use drop_all only for dev/testing!
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables checked/created.")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}", exc_info=True)
            # Consider raising an error to stop startup if DB is critical
    # Ensure data storage directory exists (redundant check is ok)
    DATA_DIR = os.path.join("backend", "data_storage")
    try: os.makedirs(DATA_DIR, exist_ok=True)
    except OSError as e: logger.error(f"Could not create data storage directory '{DATA_DIR}': {e}")


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# --- CORS Middleware ---
logger.info(f"Allowed CORS origins: {settings.ALLOWED_ORIGINS}")
if not settings.ALLOWED_ORIGINS: logger.warning("CORS origins list empty!")
app.add_middleware( CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS if settings.ALLOWED_ORIGINS else [], allow_credentials=True, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])

# --- Mount API Router ---
app.include_router(api_v1_endpoints.router, prefix=settings.API_V1_STR) # Mount router from endpoints.py

# --- Root Endpoint (Health Check) ---
@app.get("/", tags=["Health"])
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "status": "healthy"}



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
# (Defining all models here for single-file structure)
class ContactFormInput(BaseModel): name: str; email: EmailStr; company: Optional[str] = None; phone: Optional[str] = None; subject: str; message: str
class ContactSubmitResponse(BaseModel): message: str; request_id: str; status: str
class TrackedRequest(BaseModel): request_id: str; timestamp: datetime.datetime; status: str; subject: str
class TrackingResponse(BaseModel): identifier: str; requests: List[TrackedRequest]
class HireConsultantForm(BaseModel): contact_name: str = Field(...); contact_email: EmailStr; contact_phone: Optional[str] = None; contact_company: Optional[str] = None; industry: str = Field(...); business_function: str = Field(...); services_needed: List[str] = Field([]); project_timeline: str = Field(...); start_date: Optional[datetime.date] = None; resources_required: Optional[str] = None; location: Optional[str] = None; work_type: str = Field(...); experience_needed: Optional[str] = None; skills_needed: Optional[str] = None; project_description: str = Field(..., min_length=10)
class HireSubmitResponse(BaseModel): message: str; hire_request_id: str; status: str
class StartupInfoInput(BaseModel): # Includes Berkus fields
    company_name: str = Field(..., examples=["Acme Widgets"]); industry: str = Field(...); stage: str = Field(...)
    problem_solved: str = Field(..., min_length=10); solution: str = Field(..., min_length=10)
    target_market: str = Field(..., min_length=10); business_model: str = Field(..., min_length=10)
    team_size: Optional[int] = Field(default=1, ge=1); funding_raised_usd: Optional[float] = Field(default=0, ge=0)
    description: str = Field(..., min_length=20)
    has_prototype: bool = Field(False); management_summary: Optional[str] = Field(None, max_length=1000)
    strategic_partnerships: Optional[str] = Field(None, max_length=1000)
    sales_traction_summary: Optional[str] = Field(None, max_length=1000)
class StartupAnalysisResult(BaseModel): analysis_text: Optional[str] = None; error_message: Optional[str] = None; disclaimer: str = "AI analysis provides estimates..." # Default disclaimer
class AiToolQuery(BaseModel): user_query: str = Field(..., min_length=5, max_length=1500); service_context: Dict[str, Any] = Field(...)
class AiToolResponse(BaseModel): ai_response: str; error_message: Optional[str] = None


# --- Static Content Data Definitions ---
# (Ideally load from file/DB)
hero_content = {
    "headline": "Drive business growth with your own AI",
    "subheadline": "Partnering with industry leaders to solve their toughest challenges and capture their greatest opportunities through strategic insight and digital innovation.",
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
        "id": "prod_ai_analyzer", "name": "AI Financial Analyzer",
        "tagline": "Unlock insights from your financial data.",
        "description": "Upload your P&L or other statements (.xlsx, .csv, .docx, .txt) for automated insights and conceptual SWOT analysis. (Beta)",
        "img_placeholder": "https://placehold.co/350x200/0056b3/FFFFFF?text=AI+Analyzer",
        "link": "/financial-analyzer"
    },
    {
        "id": "prod_startup_consult", "name": "Startup Consultation AI",
        "tagline": "Get AI-driven feedback for your venture.",
        "description": "Input key metrics about your startup for AI consultation on strategy, risks, opportunities, and valuation factors. Includes placeholder reports & case studies. (Beta)",
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
        "icon": "fas fa-cogs",
        "prompt_suggestions": [ # NEW FIELD
            "What are the key red flags to look for during tech due diligence?",
            "Assess the scalability of [specific technology/architecture] mentioned in the uploaded file.",
            "Compare the pros and cons of [Tool A] vs [Tool B] for infrastructure.",
            "Generate a checklist for evaluating a target company's engineering team.",
        ] # Example icon
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
            "Executive summary marketing financial outputs captured from the steps followed in the engagement including summary financials. (Length can vary 5-10 pages).",
            "Excel file work outlining detailed financial and operational plan as well as having data models showing revenue and financial analysis, business valuation summary and output.",
            "Action items and pain points having a comprehensive list of areas that require improvement from the product/service offered and technology and changes for improvement."
        ],
         "icon": "fas fa-briefcase"
        "prompt_suggestions": [
            "Analyze the market size and growth potential based on the file.",
            "Identify key competitors mentioned and their potential weaknesses.",
            "What are standard frameworks for assessing commercial viability?",
            "Evaluate the customer acquisition strategy described.",
        ]
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
            "An Investor pitch deck containing information about company overview, market, product/service description, analysis, unique selling points, business model analysis as well as revenue generation plans (Length 20-25 pages).",
            "An action plan containing each databook providing detailed financial projections, detailed revenue structure, expense projections and cash flow analysis."
        ],
         "icon": "fas fa-file-powerpoint"
        "prompt_suggestions": [
            "Critique the value proposition based on the uploaded pitch deck draft.",
            "What key financial projections should I include?",
            "Suggest ways to improve the market analysis slide.",
            "Help me structure the 'Use of Funds' section.",
        ]
    },
    {
        "id": "gtm_strategy",
        "name": "Go To Market Strategy",
        "description": "The goal of GO TO MARKET research is to develop a comprehensive plan that maximises the chances of success for a new product or service while minimizing the risk of failure.",
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
            "A complete data book from the marketing and sales outlining the framework (About 30-40 pages depending on the engagement).",
            "A complete financial model outlining the marketing and sales team budget and deep dive financial analysis as well as overall cost analysis and market prioritization report (15-20 Pages).",
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
            "Detailed Financial plan containing Financial highlights and narrative. (10-15 pages)."
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
# Simple check, logs warnings during this check
if AI_LIB_AVAILABLE and GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        ai_model = genai.GenerativeModel(model_name="gemini-1.5-flash") # Or other suitable model
        logger.info("Gemini AI Model configured successfully.")
    except Exception as e: logger.error(f"Error configuring Gemini AI Model: {e}", exc_info=True); ai_model = None
else: logger.warning("AI Service disabled (Check API key in .env & google-generativeai install).")


# --- FastAPI App Setup ---
app = FastAPI(title="ZAlpha Consulting Backend API")

# --- CORS Middleware ---
default_frontend_url = "http://localhost:3001"
frontend_url_from_env = os.getenv("FRONTEND_URL", default_frontend_url)
origins = list(set([frontend_url_from_env, "http://localhost:3000"] + os.getenv("EXTRA_ALLOWED_ORIGINS", "").split(',')))
origins = [o.strip() for o in origins if o] # Clean up empty strings from split
logger.info(f"Configuring CORS for origins: {origins}")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])


# --- Helper Functions ---
def save_to_csv(filepath: str, fieldnames: List[str], row_data: Dict[str, Any]):
    """Generic helper to append a row to CSV. Returns True on success, False on failure."""
    dir_name = os.path.dirname(filepath); os.makedirs(dir_name, exist_ok=True)
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
async def get_startup_analysis(startup_data: StartupInput) -> str:
    """Generates AI analysis for startup including Berkus factors and trends."""
    if not ai_model: return "Error: AI Service not configured correctly."
    logger.info(f"Generating startup analysis for: {startup_data.company_name}")
    try:
        # --- Using the detailed prompt from Response #69 ---
        prompt = f"""
        Analyze the following early-stage startup based ONLY on the provided data. Act as a VC analyst providing initial feedback.

        **Startup Data:**
        - Company: {startup_data.company_name} | Industry: {startup_data.industry} | Stage: {startup_data.stage}
        - Problem: {startup_data.problem_solved} | Solution: {startup_data.solution}
        - Target Market: {startup_data.target_market} | Business Model: {startup_data.business_model}
        - Team Size: {startup_data.team_size or 'N/A'} | Funding Raised (USD): ${startup_data.funding_raised_usd or 0:,.0f}
        - Description: {startup_data.description}
        - Has Prototype/MVP?: {'Yes' if startup_data.has_prototype else 'No'}
        - Management Summary: {startup_data.management_summary or 'Not provided'}
        - Strategic Relationships: {startup_data.strategic_partnerships or 'Not provided'}
        - Sales Traction/Rollout: {startup_data.sales_traction_summary or 'Not provided'}

        **Analysis Report:**

        ## 1. Overall Assessment & Industry Context
        Provide a brief assessment of the startup's potential. Briefly discuss 1-2 **major recent trends or potential disruptions** you know about within the '{startup_data.industry}' industry that could impact this startup. (Acknowledge knowledge cutoff limitations).

        ## 2. Valuation Estimate (Conceptual)
        Evaluate the five critical criteria based ONLY on the data. Assign a qualitative score (Weak/Moderate/Strong/Very Strong) and value component ($0k - $500k max each). Sum for conceptual pre-revenue estimate. Explain briefly.
        - **Sound Idea (Value $0-500k):** [Evaluation] -> $Value
        - **Prototype/MVP (Value $0-500k):** [Evaluation] -> $Value
        - **Quality Management Team (Value $0-500k):** [Evaluation] -> $Value
        - **Strategic Relationships (Value $0-500k):** [Evaluation] -> $Value
        - **Product Rollout/Sales (Value $0-500k):** [Evaluation] -> $Value
        - **Total Berkus Estimate:** $Sum

        ## 3. SWOT Factors (Inferred from Financials/Data)
        Infer potential SWOT elements based *only* on provided data:
        - **Strengths:** (e.g., Problem/Solution fit? Team hint? Traction?)
        - **Weaknesses:** (e.g., No prototype? Funding? Team gap?)
        - **Opportunities:** (e.g., Large market? Partnership potential?)
        - **Threats:** (e.g., Competition implied? Funding need?)
        *Frame as possibilities requiring validation.*

        ## 4. Other Valuation Considerations
        Briefly mention 1-2 other factors relevant for a '{startup_data.stage}' stage startup in '{startup_data.industry}' (e.g., Scalability, Defensibility, Market Size).

        ## 5. Recommendations
        Provide 2-3 actionable, high-level recommendations.

        ## Disclaimer
        **Disclaimer:** This AI analysis provides estimates and general insights based solely on the provided data and its internal knowledge base (which may have limitations in recency and depth). Valuations, especially Berkus estimates, are highly subjective and conceptual examples. This does not constitute financial, investment, or professional business advice. Consult qualified human experts for any decisions.
        """
        response = await ai_model.generate_content_async(prompt)
        if not response.parts: raise Exception("AI response blocked or empty.") # Raise exception on block
        response_text = response.text
        # Simple check for disclaimer, add if missing
        if "Disclaimer: This AI analysis provides estimates" not in response_text: response_text += "\n\nDisclaimer: ..."
        logger.info(f"Successfully generated enhanced startup analysis for {startup_data.company_name}.")
        return response_text
    except Exception as e:
        logger.error(f"Error generating startup analysis: {traceback.format_exc()}")
        return f"Error: An unexpected error occurred during AI analysis: {e}"

# Conceptual update for get_contextual_ai_response in main.py or ai_service.py
from app.models.analysis import IndustryIntel # Import the intel model if using backend processing

async def get_consulting_cag_response(
    service_context: Dict[str, Any],
    user_query: str,
    file_excerpt: Optional[str] = None
    ) -> str:
    """Generates tailored consulting solutions using AI and web search."""
    if not ai_model: return "Error: AI Service not configured."

    service_name = service_context.get("name", "consulting")
    # --- 1. Generate Search Queries ---
    # (Based on service_name, user_query, extract keywords etc.)
    search_queries = [
        f"latest trends relevant to {service_name} and {user_query}",
        f"{service_name} frameworks OR methodologies",
        f"case study {service_name} {user_query[:50]}", # Truncate query for search
        f"recent news impacting {service_name}"
    ]
    logger.info(f"Generated search queries: {search_queries}")

    # --- 2. Execute Search (Requires integrated tool call) ---
    search_results_raw = None
    search_snippets = []
    try:
        # --- >>> TOOL_CODE integration needed here <<< ---
        # This is where you'd invoke the search tool with 'search_queries'
        # search_results_raw = await your_search_tool_function(search_queries)
        logger.warning("Web search execution skipped (tool call not implemented in this example).")
        # --- >>> Placeholder if no tool <<< ---
        search_snippets = ["Search result placeholder 1: Framework X is often used.", "Search result placeholder 2: Recent news indicates market shift Y."]

        # --- 3. Process Search Results ---
        # (If search tool was called, process search_results_raw here)
        # - Filter for relevance (keywords, source reliability)
        # - Extract titles, links, useful snippets
        # - Limit the number of snippets (e.g., top 5-7)
        # - Format them clearly
        # Example processing:
        # if search_results_raw:
        #     processed_snippets = []
        #     for i, result in enumerate(search_results_raw.get('results', [])[:7]): # Limit results
        #         title = result.get('title', 'N/A')
        #         snippet = result.get('snippet', 'N/A').replace('\n', ' ')
        #         link = result.get('link', '#')
        #         processed_snippets.append(f"{i+1}. Title: {title}\n   Snippet: {snippet}\n   Source: {link}")
        #     search_snippets = processed_snippets if processed_snippets else ["No relevant external info found."]

    except Exception as search_err:
        logger.error(f"Error during web search processing: {search_err}", exc_info=True)
        search_snippets = ["[Error occurred during information retrieval.]"]

    # --- 4. Construct Master Prompt ---
    prompt = f"""
    **Role:** You are an expert AI consultant specializing in **'{service_name}'**.
    **Objective:** Synthesize information from internal knowledge (theories, textbooks, general cases), provided context, user query, optional file excerpt, and recent web search results to generate a tailored, actionable solution or set of recommendations.

    **Service Context:** {service_context.get("description", "N/A")}
    **User Query:** {user_query}
    {f'**File Excerpt:** {file_excerpt}' if file_excerpt else ''}

    **Retrieved Information (Web Search Snippets - use critically):**
    ```
    {chr(10).join(search_snippets) if search_snippets else "No specific external information retrieved for this query."}
    ```

    **Instructions:**
    1.  Analyze the user query in light of the service context.
    2.  Evaluate the relevance and insights from the file excerpt (if provided) and the retrieved web information.
    3.  Synthesize these inputs with your internal knowledge of relevant theories, frameworks (mention them briefly if applicable), and general best practices for '{service_name}'.
    4.  Provide a structured response outlining potential solutions, strategies, or actionable steps tailored to the user's query.
    5.  Reference specific insights from the retrieved information where appropriate (e.g., "Recent trends suggest X..." or "Framework Y could be applied by...").
    6.  Acknowledge limitations if information is conflicting or insufficient. Prioritize accuracy and relevance.
    7.  Conclude with the standard disclaimer.

    **Consulting Solution/Recommendations:**
    [AI Response Here]

    Disclaimer: AI responses are informational... Consult human experts.
    """

    # --- 5. Call LLM ---
    try:
        logger.info(f"Sending synthesized CAG prompt for '{service_name}'...")
        response = await ai_model.generate_content_async(prompt)
        if not response.parts: raise Exception(f"AI CAG response blocked ({response.prompt_feedback.block_reason})")
        response_text = response.text.strip();
        if "Disclaimer:" not in response_text: response_text += "\n\nDisclaimer: ..."
        logger.info("CAG response generated successfully.")
        return response_text
    except Exception as ai_err:
         logger.error(f"CAG AI generation error: {traceback.format_exc()}"); return f"Error: AI generation failed: {ai_err}"

except Exception as e:
     logger.error(f"Overall CAG error: {traceback.format_exc()}"); return f"Error: Could not process CAG request: {e}"

# --- API Endpoints ---
API_V1_STR = "/api/v1"
router = APIRouter(prefix=API_V1_STR, tags=["APIv1"]) # Use single router

@router.get("/content", status_code=status.HTTP_200_OK)
async def endpoint_get_website_content():
    logger.info(f"GET /content requested")
    # Using data defined globally in this file
    return { "hero": hero_content, "services": services_data, "clients": clients_data, "testimonials": testimonials_data, "products": products_data, "custom_consulting_packages": custom_consulting_packages, "current_year": datetime.datetime.now().year }

@router.post("/contact", response_model=ContactSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def endpoint_submit_contact_form(form_data: ContactFormInput):
    logger.info(f"POST /contact received from {form_data.email}")
    if not all([form_data.name, form_data.email, form_data.subject, form_data.message]): raise HTTPException(400, "Missing required fields.")
    request_id = f"REQ-{str(uuid.uuid4())[:8].upper()}"; status = "Received"; timestamp = datetime.datetime.now()
    request_data = {"request_id": request_id, "timestamp": timestamp, "status": status, **form_data.model_dump()}
    try:
        request_store.append(request_data) # Store in memory for tracking
        logger.info(f"Contact Request {request_id} stored in memory.")
        # Save to CSV (WARNING: Ephemeral)
        contact_fieldnames = ["request_id", "timestamp", "status", "name", "email", "company", "phone", "subject", "message"]
        if not save_to_csv(CONTACTS_FILE, contact_fieldnames, request_data): raise RuntimeError("Failed to save contact to CSV") # Make save failure critical
        return ContactSubmitResponse(message="Inquiry received! Your request ID:", request_id=request_id, status=status)
    except Exception as e: logger.error(f"Error processing contact {form_data.email}: {e}", exc_info=True); raise HTTPException(500, "Server error processing contact.")

@router.get("/track", response_model=TrackingResponse, status_code=status.HTTP_200_OK)
async def endpoint_track_requests(identifier: str = Query(...)):
    logger.info(f"GET /track received for identifier: {identifier}")
    if not identifier: raise HTTPException(400, "Identifier required.")
    matching_requests: List[TrackedRequest] = []
    try: # Query IN-MEMORY list (Replace with DB)
        for req in request_store: # Only searches contact requests currently
            if (req.get('email') and req['email'].lower() == identifier.lower()) or \
               (req.get('phone') and req['phone'] == identifier):
                matching_requests.append(TrackedRequest(request_id=req.get("request_id"), timestamp=req.get("timestamp"), status=req.get("status"), subject=req.get("subject")))
        return TrackingResponse(identifier=identifier, requests=matching_requests)
    except Exception as e: logger.error(f"Error tracking: {e}", exc_info=True); raise HTTPException(500, "Error tracking requests.")

@router.post("/hire", response_model=HireSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def endpoint_submit_hire_request(form_data: HireConsultantForm):
    logger.info(f"POST /hire received from {form_data.contact_email}")
    if not all([form_data.contact_name, form_data.contact_email, form_data.industry, form_data.business_function, form_data.project_timeline, form_data.work_type, form_data.project_description]):
        raise HTTPException(400, "Missing required hire request fields.")
    hire_request_id = f"HIRE-{str(uuid.uuid4())[:8].upper()}"; status = "Hire Request Received"; timestamp = datetime.datetime.now()
    hire_data = {"hire_request_id": hire_request_id, "timestamp": timestamp, "status": status, **form_data.model_dump()}
    try:
        # Save hire request to CSV (WARNING: Ephemeral)
        hire_fieldnames = ["hire_request_id", "timestamp", "status", "contact_name", "contact_email", "contact_phone", "contact_company", "industry", "business_function", "services_needed", "project_timeline", "start_date", "resources_required", "location", "work_type", "experience_needed", "skills_needed", "project_description"]
        save_data = hire_data.copy(); save_data["services_needed"] = ", ".join(form_data.services_needed) if form_data.services_needed else ""; save_data["start_date"] = form_data.start_date.isoformat() if form_data.start_date else ""
        if not save_to_csv(HIRE_REQUESTS_FILE, hire_fieldnames, save_data): raise RuntimeError("Failed to save hire request to CSV")
        return HireSubmitResponse(message="Hire request submitted! We will review.", hire_request_id=hire_request_id, status=status)
    except Exception as e: logger.error(f"Error processing hire request {form_data.contact_email}: {e}", exc_info=True); raise HTTPException(500, "Server error processing hire request.")

# UPDATED Startup Analysis Endpoint
@router.post("/analyze/startup", response_model=StartupAnalysisResult, status_code=status.HTTP_200_OK)
async def endpoint_analyze_startup(info: StartupInput):
    logger.info(f"POST /analyze/startup received for: {info.company_name}")
    try:
        analysis_result_text = await get_startup_analysis(info) # Call updated function
        if analysis_result_text.startswith("Error:"):
            logger.warning(f"Startup analysis failed for {info.company_name}: {analysis_result_text}")
            return StartupAnalysisResult(analysis_text=None, error_message=analysis_result_text)
        return StartupAnalysisResult(analysis_text=analysis_result_text, error_message=None)
    except Exception as e: logger.error(f"Error in startup analysis endpoint {info.company_name}: {e}", exc_info=True); return StartupAnalysisResult(analysis_text=None, error_message=f"Unexpected server error: {e}")

@router.post("/ai-tool", response_model=AiToolResponse, status_code=status.HTTP_200_OK)
async def endpoint_ai_tool_query(query_data: AiToolQuery):
    logger.info(f"POST /ai-tool received for service: {query_data.service_context.get('name', 'Unknown')}")
    if not query_data.service_context or not query_data.user_query: raise HTTPException(400, "Missing context or query.")
    try:
        ai_response_text = await get_consulting_cag_response(service_context=query_data.service_context, user_query=query_data.user_query,file_excerpt=file_excerpt_text)
        if ai_response_text.startswith("Error:"): return AiToolResponse(ai_response="Could not generate response.", error_message=ai_response_text)
        return AiToolResponse(ai_response=ai_response_text)
    except Exception as e: logger.error(f"Error in AI tool endpoint: {e}", exc_info=True); raise HTTPException(500, "Error during AI processing.")

# Mount the router
app.include_router(router)

# Health check at root
@app.get("/")
async def health_check(): return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

# --- Uvicorn Run Command (for reference) ---
# From project root: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --env-file backend/.env
