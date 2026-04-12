from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
