from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List, Union,Optional
import os # Import os

class Settings(BaseSettings):
    # Adjust env_file path if running uvicorn from project root vs backend dir
    model_config = SettingsConfigDict(env_file='C:/Users/rbihe/Downloads/consulting/backend/.env', env_file_encoding='utf-8', extra='ignore')

    APP_NAME: str = "SynergyPro Consulting API"
    API_V1_STR: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: List[str] = []
    DATABASE_URL: Optional[str] = None 

    GOOGLE_API_KEY: str | None = None
    # OPENAI_API_KEY: str | None = None

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    CONTACT_TO_EMAIL: str | None = None

    # Derive ALLOWED_ORIGINS after loading
    def __init__(self, **values):
        super().__init__(**values)
        # Ensure provided FRONTEND_URL is always included + localhost for dev
        self.ALLOWED_ORIGINS = list(set([
            self.FRONTEND_URL,
            "http://localhost:3000", # Keep for local dev convenience
            # Add other static origins if needed
        ]))

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()