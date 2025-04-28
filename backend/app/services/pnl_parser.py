# --- backend/app/services/pnl_parser.py ---
import pandas as pd
import io
from app.models.analysis import PnlInputData
from typing import Dict, Any
import re
import logging
import zipfile # Needed for python-docx

# Try importing docx, handle if not installed
try:
    import docx
    HAS_DOCX = True
except ImportError:
    docx = None # Make docx variable None if import fails
    HAS_DOCX = False
    logging.warning("python-docx library not found. DOCX parsing will be disabled.")


logger = logging.getLogger(__name__)

# --- WARNING ---
# Parsing is HIGHLY SIMPLIFIED and assumes clean structures.
# It WILL FAIL on most real-world complex documents.
# PDF/OCR requires external tools (Tesseract) and libraries (pdfplumber/pytesseract) NOT included here.

KEYWORDS = { # Needs significant refinement for real P&Ls
    "revenue": ["revenue", "sales", "turnover", "net sales", "total revenue"],
    "cogs": ["cost of goods sold", "cost of sales", "cost of revenue"],
    "gross_profit": ["gross profit", "gross margin"],
    "operating_expenses_total": ["total operating expenses", "opex", "operating expenses"],
    "operating_income": ["operating income", "operating profit", "income from operations", "ebit"],
    "interest_expense": ["interest expense", "finance costs", "interest and finance costs"],
    "taxes": ["income tax", "tax expense", "provision for income tax"],
    "net_income": ["net income", "net profit", "profit for the period", "earnings after tax", "net earnings"]
}
NUMBER_REGEX = re.compile(r"([$€£]?\s*\(\s*[$€£]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*\)|[$€£]?\s*(-?)\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?)")

def clean_value(value_str: Any) -> float | None:
    # ...(Same clean_value function as previously provided)...
    if pd.isna(value_str): return None
    if isinstance(value_str, (int, float)): return float(value_str)
    if not isinstance(value_str, str): return None
    value_str = value_str.strip()
    match = NUMBER_REGEX.search(value_str)
    if not match: return None
    num_part = match.group(2) if match.group(2) else match.group(0)
    is_negative_paren = match.group(1) and match.group(1).startswith('(')
    is_negative_sign = match.group(3) == '-'
    num_str = re.sub(r"[$,€£\s,]", "", num_part)
    try:
        number = float(num_str)
        if is_negative_paren or is_negative_sign: return -abs(number)
        return number
    except ValueError: return None


def parse_simple_text_or_docx(content_stream: io.BytesIO, filename: str) -> str:
    """Reads text from TXT or DOCX stream."""
    text_content = ""
    file_lower = filename.lower()
    if file_lower.endswith('.docx'):
        if not HAS_DOCX:
            raise ValueError("DOCX processing requires the 'python-docx' library to be installed.")
        try:
            document = docx.Document(content_stream)
            text_content = "\n".join([para.text for para in document.paragraphs if para.text]) # Ignore empty paragraphs
            logger.info(f"Successfully read text content from DOCX: {filename}")
        except Exception as e:
            logger.error(f"Failed to read DOCX file {filename}: {e}", exc_info=True)
            raise ValueError(f"Failed to read DOCX file: {e}")
    elif file_lower.endswith('.txt'):
        try:
            # Try common encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    content_stream.seek(0) # Reset stream position
                    text_content = content_stream.read().decode(encoding)
                    logger.info(f"Successfully read text content from TXT ({encoding}): {filename}")
                    break # Stop if successful
                except UnicodeDecodeError:
                    continue # Try next encoding
            if not text_content: # If no encoding worked
                 raise ValueError("Could not decode TXT file with common encodings.")
        except Exception as e:
            logger.error(f"Failed to read TXT file {filename}: {e}", exc_info=True)
            raise ValueError(f"Failed to read TXT file: {e}")
    else:
         raise ValueError("Unsupported text format for simple text parser.")
    return text_content


async def parse_pnl_file(file_contents: bytes, filename: str) -> PnlInputData:
    """
    Parses P&L from Excel/CSV/TXT/DOCX (simplified).
    Returns a PnlInputData object. Raises ValueError on issues.
    """
    df = None
    text_content = None
    file_lower = filename.lower()
    content_stream = io.BytesIO(file_contents)
    logger.info(f"Starting P&L parsing for file: {filename} (Type detected: {file_lower.split('.')[-1]})")

    try:
        if file_lower.endswith('.xlsx'):
            df = pd.read_excel(content_stream, sheet_name=0, header=None)
        elif file_lower.endswith('.csv'):
            df = pd.read_csv(content_stream, header=None)
        elif file_lower.endswith(('.txt', '.docx')):
            text_content = parse_simple_text_or_docx(content_stream, filename)
            lines = [line.strip() for line in text_content.splitlines() if line.strip()]
            data = []
            # Very basic Key: Value or Key Value structure detection
            for line in lines:
                # Try splitting by common delimiters first
                parts = re.split(r':\s+|\t+|\s{2,}', line, 1) # Split by colon+space OR tab OR multiple spaces
                if len(parts) == 2:
                    data.append([parts[0].strip(), parts[1].strip()])
                else:
                    # Fallback: maybe space separated? Take first word block as key, rest as value
                    words = line.split(None, 1)
                    if len(words) == 2:
                         data.append([words[0], words[1]])
                    elif len(words) == 1: # Handle lines with only label or only value? Maybe skip.
                         pass
            if data:
                 df = pd.DataFrame(data, columns=['Description', 'Value_Raw']) # Use different name to avoid clash
                 logger.info(f"Parsed {len(data)} lines from text/docx into DataFrame.")
            else:
                 raise ValueError("Could not parse text/docx file into a structured format.")
        # --- PLACEHOLDER FOR PDF/OCR ---
        # elif file_lower.endswith('.pdf'):
        #     raise ValueError("PDF parsing is not implemented.")
        else:
            raise ValueError("Unsupported file type.")

    except ValueError as ve: # Catch parsing/format errors
         logger.error(f"Parsing/Format Error for {filename}: {ve}")
         raise ve # Re-raise specific error
    except Exception as e:
        logger.error(f"Failed to read/process file {filename}: {e}", exc_info=True)
        raise ValueError(f"Failed to read/process file: {e}") # Raise generic error

    if df is None or df.empty:
        raise ValueError("File is empty or could not be parsed into a usable DataFrame.")

    # --- Keyword-Based Extraction ---
    extracted_values: Dict[str, Any] = {"period": "Unknown"}
    found_items = set()

    # Attempt to find description/value columns more intelligently
    desc_col = None
    val_col = None
    possible_desc_cols = [c for c in df.columns if df[c].dtype == 'object' or pd.api.types.is_string_dtype(df[c])]
    possible_val_cols = [c for c in df.columns if df[c].apply(lambda x: clean_value(x) is not None).any()]

    if possible_desc_cols: desc_col = possible_desc_cols[0] # Take first likely description column
    if possible_val_cols: val_col = possible_val_cols[0] # Take first likely value column

    if desc_col is None or val_col is None:
        logger.error(f"Could not identify description/value columns reliably in {filename}.")
        raise ValueError("Could not reliably identify description and value columns.")

    logger.info(f"Attempting extraction on {filename} using Desc Col: '{desc_col}', Val Col: '{val_col}'")

    for index, row in df.iterrows():
        description = str(row[desc_col]).strip().lower() if pd.notna(row[desc_col]) else ""
        value_raw = row[val_col]
        if not description: continue

        value = None
        if isinstance(value_raw, (int, float)) and pd.notna(value_raw):
            value = float(value_raw)
        else:
            value = clean_value(str(value_raw))

        if value is None: continue

        # Match keywords (only take first match per key)
        for key, terms in KEYWORDS.items():
            if key not in found_items:
                for term in terms:
                    # Use regex for potentially better matching (word boundaries)
                    if re.search(r'\b' + re.escape(term) + r'\b', description):
                        extracted_values[key] = value
                        found_items.add(key)
                        logger.info(f"Found '{key}' (term: '{term}' in row {index}): {value}")
                        # Maybe don't break here, allow finding more specific terms later? Depends on P&L structure.
                        # For now, break to take first match per row for simplicity.
                        break # Matched this key, move to next key for this row


    # --- Data Model Creation & Post-Processing ---
    pnl_data = PnlInputData(
         revenue=extracted_values.get("revenue"), cogs=extracted_values.get("cogs"),
         gross_profit=extracted_values.get("gross_profit"), operating_income=extracted_values.get("operating_income"),
         interest_expense=extracted_values.get("interest_expense"), taxes=extracted_values.get("taxes"),
         net_income=extracted_values.get("net_income"), period=extracted_values.get("period")
         # OpEx dict needs more work
    )
    # Basic calculation if components exist but total is missing
    if pnl_data.revenue and pnl_data.cogs and pnl_data.gross_profit is None:
        pnl_data.gross_profit = pnl_data.revenue - pnl_data.cogs
        logger.info(f"Calculated Gross Profit: {pnl_data.gross_profit}")
    # Add more checks (e.g., OpIncome = GP - OpEx Total) if OpEx is parsed

    if pnl_data.revenue is None:
         logger.warning(f"Revenue could not be extracted from {filename}.")

    logger.info(f"P&L parsing completed for {filename}. Extracted: {pnl_data.model_dump(exclude_none=True)}")
    return pnl_data