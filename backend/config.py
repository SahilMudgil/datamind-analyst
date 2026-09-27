import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    # App Database (PostgreSQL + pgvector)
    DATABASE_URL: str = "postgresql://app_user:app_password@localhost:5433/app_db"

    # Target Database (Read-only demo database)
    TARGET_DB_URL: str = "postgresql://readonly_agent:readonly_secure_pass@localhost:5433/ecommerce_db"

    # LLM API Keys
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-004"

    # JWT Authentication
    JWT_SECRET_KEY: str = "antigravity_super_secret_jwt_key_2026_text_to_sql"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours

    # Server & CORS
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173"

    # Agent Guardrails
    QUERY_TIMEOUT_SECONDS: int = 10
    MAX_QUERY_RETRIES: int = 2
    DEFAULT_ROW_LIMIT: int = 100

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
