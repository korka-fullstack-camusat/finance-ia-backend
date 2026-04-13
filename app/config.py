from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

_BASE_DIR = Path(__file__).resolve().parent.parent  # racine du backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "mistral-small-latest"
    DATABASE_URL: str = "sqlite:///./financeai.db"
    REDIS_URL: str = "redis://localhost:6379"
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@financeai.com"
    SLACK_WEBHOOK_URL: str = ""
    NOTIFICATION_EMAIL: str = ""
    CORS_ORIGINS: str = "http://localhost:3000"
    SECRET_KEY: str = "change-me-in-production"
    UPLOAD_DIR: str = "uploads"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
