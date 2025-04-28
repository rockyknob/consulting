# --- backend/app/services/ai_service.py ---
# Updated: Tuesday, April 22, 2025 at 11:55 PM IST (New Delhi)

# Use correct import path if using the structured app layout
from app.core.config import settings
from app.models.analysis import StartupInfoInput # Import updated model
import google.generativeai as genai
import traceback
import logging
from typing import Dict, Any # For type hinting

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Conditional Library Check ---
AI_LIB_AVAILABLE = False
try:
    import google.generativeai as genai
    AI_LIB_AVAILABLE = True
except ImportError:
    genai = None
    logger.warning("google-generativeai library not found. AI features disabled.")

# --- AI Model Configuration ---
ai_model = None
# Check if library is available first
if AI_LIB_AVAILABLE:
    GOOGLE_API_KEY = settings.GOOGLE_API_KEY # Get key from settings object
    if GOOGLE_API_KEY:
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            generation_config = { # Consistent config
                "temperature": 0.6, "top_p": 1, "top_k": 1, "max_output_tokens": 4096, # Increased tokens
            }
            safety_settings = [ # Consistent safety
                {"category": f"HARM_CATEGORY_{cat}", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
                for cat in ["HARASSMENT", "HATE_SPEECH", "SEXUALLY_EXPLICIT", "DANGEROUS_CONTENT"]
            ]
            ai_model = genai.GenerativeModel(
                model_name="gemini-1.5-flash", # Ensure model name is correct/available
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            logger.info("Gemini AI Model configured successfully in ai_service.")
        except Exception as e:
            logger.error(f"Error configuring Gemini AI Model in ai_service: {e}", exc_info=True)
            ai_model = None # Ensure it's None if config fails
    else:
        logger.warning("GOOGLE_API_KEY not found via settings. AI Service disabled.")
else:
     logger.warning("AI Library not available. AI Service disabled.")


# --- Existing AI Functions (Keep these) ---

async def get_pnl_insights(data: dict) -> str:
    """Generates insights from summarized P&L data using AI."""
    if not ai_model: return "Error: AI Service not configured correctly."
    # ...(Keep prompt and logic from Response #83)...
    try:
        prompt = f"Analyze P&L data:\n{data}\n\nProvide analysis focusing on Profitability and Potential Focus Areas..." # Truncated for brevity
        prompt += "\n\nStart with: '**AI-Generated Financial Snapshot Analysis:**'"
        prompt += "\nEnd with: '**Disclaimer:** This AI analysis is automated... Consult with a qualified financial advisor.'"
        logger.info("Sending P&L analysis prompt to AI...")
        response = await ai_model.generate_content_async(prompt)
        if not response.parts: raise Exception("AI response blocked or empty.")
        return response.text
    except Exception as e: logger.error(f"AI PNL error: {traceback.format_exc()}"); return f"Error generating PNL insights: {e}"

async def get_financial_swot(data: dict) -> str:
    """Generates a speculative SWOT analysis based only on financial data."""
    if not ai_model: return "Error: AI Service not configured correctly."
    # ...(Keep prompt and logic from Response #83)...
    try:
        prompt = f"Analyze financials for conceptual SWOT:\n{data}\n\nInfer potential Strengths, Weaknesses, Opportunities, Threats based ONLY on these numbers..." # Truncated
        prompt += "\n\nStart with: '**AI-Generated Conceptual SWOT (Based ONLY on Financials):**'"
        prompt += "\nEnd with: '**Disclaimer:** This SWOT is highly speculative... Requires external validation.'"
        logger.info("Sending Financial SWOT prompt to AI...")
        response = await ai_model.generate_content_async(prompt)
        if not response.parts: raise Exception("AI response blocked or empty.")
        return response.text
    except Exception as e: logger.error(f"AI SWOT error: {traceback.format_exc()}"); return f"Error generating SWOT: {e}"

# --- Update this function in backend/main.py or ai_service.py ---

async def get_contextual_ai_response(
    service_context: Dict[str, Any],
    user_query: str,
    file_excerpt: Optional[str] = None # Renamed parameter for clarity
    ) -> str:
    """Generates AI response using service context, query, and optional file EXCERPT."""
    if not ai_model:
        return "Error: AI Service not configured correctly."

    service_name = service_context.get("name", "the selected service")
    service_desc = service_context.get("description", "N/A")
    logger.info(f"Generating AI response for service '{service_name}'. File excerpt provided: {bool(file_excerpt)}")

    # --- Build Enhanced Prompt ---
    prompt = f"""
    **Role:** You are an expert AI assistant acting as a senior consultant for SynergyPro, specializing in **'{service_name}'**.
    **Objective:** Provide an accurate, insightful, and concise response to the user's query, leveraging the specific service context and analyzing the provided file excerpt if available.

    **Service Package Context:**
    * **Name:** {service_name}
    * **Description:** {service_desc}
    * **(Implicit Factors):** Consider typical analysis factors for this type of service (e.g., for strategy: SWOT, market trends, competitive landscape; for finance: profitability, cash flow, valuation; for tech: architecture, scalability, risks).

    **User Query:**
    ```
    {user_query}
    ```

    {f'''
    **Uploaded File Content Excerpt (Beginning and End Sections Only):**
    ```
    {file_excerpt}
    ```
    ''' if file_excerpt else "**No file uploaded.**"}

    **Analysis & Response Instructions:**
    1.  **Understand Query & Context:** Fully grasp the user's question within the framework of the '{service_name}' service.
    2.  **Analyze File Excerpt (If Provided):**
        * Acknowledge you are working with only the start and end portions of the file.
        * Carefully examine the **File Content Excerpt**.
        * Determine its **relevance** to the **User Query** and the **Service Package Context**.
        * Extract key data points, statements, or themes from the excerpt that directly address the query or relate to the service's analysis factors.
        * Identify potential insights, issues, or questions raised by the excerpt *in relation to the query and service*.
    3.  **Synthesize Response:**
        * Directly answer the **User Query**.
        * Integrate relevant findings from the **File Content Excerpt** analysis (if applicable and relevant). Clearly state when information comes from the file excerpt.
        * Connect your analysis to the **Service Package Context** and its implicit factors.
        * If the excerpt lacks sufficient relevant information or seems contradictory, state that limitation clearly. Do not invent data not present in the excerpt.
        * Maintain a professional, consultative tone.
    4.  **Efficiency:** Provide the most valuable insights concisely. Prioritize accuracy.
    5.  **Disclaimer:** Conclude response with: "Disclaimer: AI responses are informational and based on provided context/excerpts. Consult human experts for critical decisions."

    **Consultant Response:**
    """

    try:
        logger.debug(f"Sending prompt to AI (excerpt length approx {len(file_excerpt or '')})...")
        # Consider adjusting generation config for speed/accuracy trade-off if needed
        response = await ai_model.generate_content_async(prompt)
        if not response.parts: raise Exception(f"AI response blocked ({response.prompt_feedback.block_reason})")
        response_text = response.text.strip();
        if "Disclaimer:" not in response_text: response_text += "\n\nDisclaimer: AI responses are informational..." # Ensure disclaimer
        logger.info("AI response generated successfully.")
        return response_text
    except Exception as e: logger.error(f"Contextual AI error: {traceback.format_exc()}"); return f"Error: AI generation failed: {e}"
# --- REVISED Startup Analysis Function ---
# --- Replace the entire function in backend/app/services/ai_service.py ---

async def get_startup_analysis(startup_data: StartupInfoInput) -> str:
    """
    Generates comprehensive AI analysis for startup including Berkus factors,
    industry trends (based on AI knowledge), SWOT factors, and recommendations.
    Returns a single formatted string (intended for Markdown display).
    """
    if not ai_model:
        logger.warning("Startup analysis attempted but AI model not available.")
        return "Error: AI Service not configured correctly."

    logger.info(f"Generating enhanced startup analysis for: {startup_data.company_name}")

    try:
        # Using the detailed prompt incorporating Berkus, Trends, SWOT factors, etc.
        prompt = f"""
        Analyze the following early-stage startup based ONLY on the provided data. Act as a VC analyst providing initial feedback.

        **Startup Data:**
        - Company: {startup_data.company_name} | Industry: {startup_data.industry} | Stage: {startup_data.stage}
        - Problem: {startup_data.problem_solved} | Solution: {startup_data.solution}
        - Target Market: {startup_data.target_market} | Business Model: {startup_data.business_model}
        - Team Size: {startup_data.team_size or 'N/A'} | Funding Raised (USD): ${startup_data.funding_raised_usd or 0:,.0f}
        - Description/Vision: {startup_data.description}
        - Has Prototype/MVP?: {'Yes' if startup_data.has_prototype else 'No'}
        - Management Summary: {startup_data.management_summary or 'Not provided'}
        - Strategic Relationships: {startup_data.strategic_partnerships or 'Not provided'}
        - Sales Traction/Rollout: {startup_data.sales_traction_summary or 'Not provided'}

        **Analysis Report (Use Markdown headings):**

        ## 1. Overall Assessment & Industry Context
        Provide a brief assessment of the startup's potential. Briefly discuss 1-2 **major recent trends or potential disruptions** you know about within the '{startup_data.industry}' industry that could impact this startup. (Acknowledge knowledge cutoff limitations).

        ## 2. Valuation Estimate (Conceptual)
        Evaluate the five key criteria based ONLY on the data. Assign a qualitative score (Weak/Moderate/Strong/Very Strong) and an estimated value component ($0k - $500k max per component, using judgment based on strength/risk reduction). Sum the components for a conceptual pre-revenue valuation estimate. Explain reasoning briefly.
        - **Sound Idea (Value $0-500k):** [Evaluation based on Problem/Solution/Market] -> $Value Assigned
        - **Prototype/MVP (Value $0-500k):** [Evaluation based on 'Has Prototype?'] -> $Value Assigned
        - **Quality Management Team (Value $0-500k):** [Evaluation based on 'Management Summary'] -> $Value Assigned
        - **Strategic Relationships (Value $0-500k):** [Evaluation based on 'Strategic Relationships'] -> $Value Assigned
        - **Product Rollout/Sales (Value $0-500k):** [Evaluation based on 'Sales Traction'] -> $Value Assigned
        - **Total Conceptual Berkus Estimate:** $Sum (e.g., $1.2M)

        ## 3. SWOT Factors (Inferred from Data)
        Infer potential SWOT elements based *only* on provided data:
        - **Strengths:** (1-2 points, e.g., Clear problem/solution? Team hint? Traction?)
        - **Weaknesses:** (1-2 points, e.g., No prototype? Funding need? Small team?)
        - **Opportunities:** (1-2 points, e.g., Large market described? Partnership potential?)
        - **Threats:** (1-2 points, e.g., Competition implied? Scalability challenges?)
        *Frame as possibilities requiring validation.*

        ## 4. Other Valuation Considerations
        Briefly mention 1-2 other factors relevant for a '{startup_data.stage}' stage startup in '{startup_data.industry}' (e.g., Scalability, Defensibility/IP, Market Size, Competition Intensity).

        ## 5. Recommendations
        Provide 2-3 actionable, high-level recommendations.

        ## Disclaimer
        **Disclaimer:** This AI analysis provides estimates and general insights based solely on the provided data and its internal knowledge base (which may have limitations in recency and depth). Valuations, especially Berkus estimates, are highly subjective and conceptual examples. This does not constitute financial, investment, or professional business advice. Consult qualified human experts for any decisions.
        """

        logger.info(f"Sending enhanced startup analysis prompt for '{startup_data.company_name}'...")
        response = await ai_model.generate_content_async(prompt) # Use async if available

        # Handle blocked response
        if not response.parts:
            block_reason = "Unknown"
            # --- CORRECTED try...except block ---
            try:
                # Check if the reason exists on the feedback object
                 if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason'):
                    block_reason = response.prompt_feedback.block_reason or "Unknown"
            except Exception:
                # Ignore potential errors accessing block_reason, keep it "Unknown"
                pass
            # --- End Correction ---
            logger.warning(f"Startup analysis AI response blocked for {startup_data.company_name}. Reason: {block_reason}")
            # Raise an exception to be caught by the endpoint handler
            raise Exception(f"Error: AI response blocked by safety settings ({block_reason}).")

        response_text = response.text
        # Simple check for disclaimer, add if missing
        disclaimer_text = "Disclaimer: This AI analysis provides estimates"
        if disclaimer_text not in response_text:
            response_text += f"\n\n{disclaimer_text} based solely on the provided data..." # Add standard disclaimer
        logger.info(f"Successfully generated enhanced startup analysis for {startup_data.company_name}.")
        return response_text

    except Exception as e:
        logger.error(f"Error generating startup analysis for {startup_data.company_name}: {traceback.format_exc()}")
        # Return specific error message to be handled by endpoint
        # Prefixing with "Error:" helps the endpoint identify it
        return f"Error: An unexpected error occurred during AI analysis: {e}"

# --- Keep other functions like get_pnl_insights, get_financial_swot, get_contextual_ai_response ---
# ...

# Note: Removed the old get_startup_consultation and get_valuation_discussion functions
# as their logic is now combined into get_startup_analysis.