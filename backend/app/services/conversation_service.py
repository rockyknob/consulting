# --- backend/app/services/conversation_service.py ---
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import conversation as conv_models # Pydantic Schemas
from app.models.conversation import Conversation, Message # SQLAlchemy Models
from app.utils.compression import compress_text, decompress_text # Import compression utils
from typing import Optional, List, Dict
import logging
import datetime

logger = logging.getLogger(__name__)

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

async def add_message(db: AsyncSession, *, conv_id: int, role: str, content: str) -> Message:
    """Adds a new message to a conversation, compressing content."""
    logger.debug(f"Adding message to conv_id={conv_id}, role={role}")
    if role not in ["user", "model"]: # Basic validation
        raise ValueError("Role must be 'user' or 'model'")
    try:
        compressed_content = compress_text(content) # Compress before saving
    except Exception as e:
        logger.error(f"Compression failed for message in conv {conv_id}: {e}", exc_info=True)
        # Save uncompressed or raise error? Let's raise to indicate problem.
        raise ValueError("Failed to compress message content for storage.")

    new_msg = Message(
        conversation_id=conv_id,
        role=role,
        content=compressed_content # Save compressed bytes
    )
    db.add(new_msg)
    await db.flush()
    await db.refresh(new_msg)
    logger.debug(f"Message added to conv {conv_id} with ID: {new_msg.id}")
    # Commit happens via get_db dependency
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

# --- Prompt Suggestions ---
# (Move to DB or config file for better management)
PROMPT_SUGGESTIONS = {
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