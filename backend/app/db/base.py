# --- backend/app/db/base.py (Corrected - REMOVE model imports) ---
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# DO NOT import your models (like User) here.
# They import Base from this file.
# Tools like Alembic can be configured to find models elsewhere.
# Your main app startup (main.py) will import models before creating tables.