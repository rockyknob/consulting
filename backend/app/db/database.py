# --- backend/app/db/database.py ---
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings # Import settings from config
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = str(settings.DATABASE_URL) # Ensure it's a string
if not DATABASE_URL:
    logger.error("FATAL: DATABASE_URL not found in environment variables!")
    # Optionally raise an error to prevent startup without DB URL
    # raise ValueError("DATABASE_URL environment variable must be set.")
    engine = None
    AsyncSessionLocal = None
else:
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
            pool_pre_ping=True
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