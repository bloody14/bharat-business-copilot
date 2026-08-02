from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://bharat:bharat_local_dev@localhost:5432/bharat_copilot"
    frontend_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    clerk_issuer_url: str | None = None
    clerk_jwks_url: str | None = None
    clerk_audience: str | None = None
    
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    
    openrouter_api_key: str | None = None
    openrouter_model: str = "openrouter/free"
    
    # Copilot Configuration
    copilot_history_limit: int = 20
    gemini_cooldown_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
