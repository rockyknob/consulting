# --- backend/app/utils/compression.py ---
import zlib
import logging

logger = logging.getLogger(__name__)

def compress_text(text: str) -> bytes:
    """Compresses text using zlib."""
    try:
        # Encode to bytes before compressing
        return zlib.compress(text.encode('utf-8'))
    except Exception as e:
        logger.error(f"Error compressing text: {e}", exc_info=True)
        # Fallback: return original text encoded if compression fails? Or raise?
        # Returning encoded original might exceed DB column size if it was large
        # Best to raise or return indicator of failure. Let's raise for now.
        raise ValueError(f"Compression failed: {e}")

def decompress_text(data: bytes) -> str:
    """Decompresses text using zlib."""
    try:
        # Decompress bytes and decode back to string
        return zlib.decompress(data).decode('utf-8')
    except zlib.error as e:
         logger.error(f"Zlib decompression error: {e}", exc_info=True)
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