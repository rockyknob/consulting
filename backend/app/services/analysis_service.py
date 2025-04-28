# --- backend/app/services/analysis_service.py ---
from app.services import pnl_parser, ai_service
# Note: Assuming models are now correctly referenced via analysis_models alias if imported in endpoints.py
# Or import directly if needed here:
from app.models.analysis import PnlInputData, PnlRatios, PnlAnalysisResult, StartupInfoInput, StartupAnalysisResult
from fastapi import UploadFile, HTTPException
import traceback
import logging

logger = logging.getLogger(__name__)

class AnalysisService:
    """Orchestrates analysis tasks for P&L and Startups."""

    async def analyze_pnl(self, file: UploadFile) -> PnlAnalysisResult:
        """Analyzes uploaded P&L file, calculates ratios, gets AI insights & SWOT."""
        filename = file.filename or "uploaded_file"
        extracted_data: PnlInputData | None = None
        ratios: PnlRatios | None = None
        ai_insights: str | None = None
        ai_swot: str | None = None # Added SWOT
        error_message: str | None = None
        # Updated disclaimer
        disclaimer = "Financial analysis based on automated parsing (best effort on provided files: XLSX, CSV, basic TXT/DOCX) and AI suggestions. SWOT is highly speculative, inferred only from financials. Verify all data and consult professionals. Results may be inaccurate/incomplete."
        logger.info(f"Starting PNL analysis process for {filename}")

        try:
            contents = await file.read()
            # 1. Parse File
            extracted_data = await pnl_parser.parse_pnl_file(contents, filename)

            # 2. Calculate Ratios (only if revenue exists)
            if extracted_data and extracted_data.revenue is not None and extracted_data.revenue != 0:
                logger.info(f"Calculating ratios for {filename}...")
                ratios = PnlRatios()
                revenue = extracted_data.revenue
                try: # Wrap ratio calculation too
                    if extracted_data.gross_profit is not None:
                        ratios.gross_margin_percent = round((extracted_data.gross_profit / revenue) * 100, 2)
                    if extracted_data.operating_income is not None:
                        ratios.operating_margin_percent = round((extracted_data.operating_income / revenue) * 100, 2)
                    if extracted_data.net_income is not None:
                        ratios.net_margin_percent = round((extracted_data.net_income / revenue) * 100, 2)
                    logger.info(f"Ratios calculated for {filename}: {ratios.model_dump(exclude_none=True)}")
                except ZeroDivisionError:
                    logger.warning(f"Division by zero error during ratio calculation for {filename} (Revenue: {revenue})")
                except Exception as ratio_error:
                     logger.error(f"Error calculating ratios for {filename}: {ratio_error}", exc_info=True)

            # 3. Get AI Insights & SWOT (if data was extracted)
            if extracted_data:
                logger.info(f"Requesting AI analysis (Insights & SWOT) for {filename}...")
                ai_payload = { # Create payload once
                    k: f"{v:,.0f}" if isinstance(v, (int, float)) else v
                    for k, v in extracted_data.model_dump(exclude_none=True).items()
                    if k != 'operating_expenses' # Exclude dicts for now
                }
                if ratios: # Add ratios if calculated
                    ai_payload.update({
                        k: v for k, v in ratios.model_dump(exclude_none=True).items() if v is not None
                    })

                # Call AI functions (sequentially is simpler for now)
                ai_insights = await ai_service.get_pnl_insights(ai_payload)
                ai_swot = await ai_service.get_financial_swot(ai_payload) # Call SWOT function

                # Check for errors from AI service
                partial_error = False
                if ai_insights and ("Error" in ai_insights or "not configured" in ai_insights or "blocked" in ai_insights):
                     logger.warning(f"AI insights generation issue for {filename}: {ai_insights}")
                     partial_error = True
                if ai_swot and ("Error" in ai_swot or "not configured" in ai_swot or "blocked" in ai_swot):
                     logger.warning(f"AI SWOT generation issue for {filename}: {ai_swot}")
                     partial_error = True
                if partial_error: error_message = (error_message or "") + " Partial AI analysis failure reported by AI service."


        except ValueError as ve: # Catch parsing value errors
            error_message = str(ve)
            logger.error(f"P&L Parsing Error for {filename}: {error_message}", exc_info=True)
        except Exception as e:
            error_message = f"An unexpected error occurred during P&L analysis: {e}"
            logger.error(f"P&L Analysis Unexpected Error for {filename}: {traceback.format_exc()}")
        finally:
             if file: await file.close() # Ensure file handle closed

        status = "Completed" if not error_message else "Error"
        logger.info(f"PNL analysis finished for {filename}. Status: {status}")
        return PnlAnalysisResult(
            filename=filename,
            processing_status=status,
            extracted_data=extracted_data,
            calculated_ratios=ratios,
            ai_insights=ai_insights,
            ai_swot_analysis=ai_swot, # Include SWOT result
            disclaimer=disclaimer,
            error_message=error_message
        )

    async def analyze_startup(self, info: StartupInfoInput) -> StartupAnalysisResult:
        """Analyzes startup information using AI."""
        # ...(Keep function as previously provided, calling both AI functions)...
        consultation: str | None = None
        valuation: str | None = None
        error_message: str | None = None
        disclaimer = "AI analysis provides general points based on limited input and may be inaccurate or incomplete. Valuation discussion is conceptual, NOT financial advice or an opinion of value. Consult with qualified professionals for business and financial decisions."
        logger.info(f"Starting startup analysis for {info.company_name}")

        try:
            logger.info(f"Requesting AI consultation for {info.company_name}...")
            consultation = await ai_service.get_startup_consultation(info)
            logger.info(f"Requesting AI valuation discussion for {info.company_name}...")
            valuation = await ai_service.get_valuation_discussion(info)

            partial_error = False
            if consultation and ("Error" in consultation or "not configured" in consultation or "blocked" in consultation):
                logger.warning(f"AI consultation issue for {info.company_name}: {consultation}")
                error_message = (error_message or "") + "AI Consultation Error. "
                partial_error = True
            if valuation and ("Error" in valuation or "not configured" in valuation or "blocked" in valuation):
                logger.warning(f"AI valuation discussion issue for {info.company_name}: {valuation}")
                error_message = (error_message or "") + "AI Valuation Discussion Error."
                partial_error = True
            if partial_error:
                 logger.warning(f"Partial errors during startup analysis for {info.company_name}")

        except Exception as e:
            error_message = f"An unexpected error occurred during startup analysis: {e}"
            logger.error(f"Startup Analysis Unexpected Error for {info.company_name}: {traceback.format_exc()}")
            consultation = consultation or "Error during processing."
            valuation = valuation or "Error during processing."

        status = "Completed" if not error_message else "Error"
        logger.info(f"Startup analysis processing finished for {info.company_name}. Status: {status}")
        return StartupAnalysisResult(
            company_name=info.company_name,
            processing_status=status,
            ai_consultation=consultation,
            valuation_discussion=valuation,
            disclaimer=disclaimer,
            error_message=error_message
        )

# Instantiate service for potential dependency injection later if needed
analysis_svc_instance = AnalysisService()