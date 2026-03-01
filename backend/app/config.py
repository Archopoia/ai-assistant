from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/wellness_db"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_RECIPE_MODEL: str = "gpt-3.5-turbo"
    OPENAI_ANALYSIS_MODEL: str = "gpt-3.5-turbo"
    
    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    # True => implicit TLS (typically port 465), False => plain/STARTTLS (typically port 587)
    SMTP_USE_TLS: bool = False
    
    # App
    APP_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    ENFORCE_HTTPS: bool = False

    # Application-level encryption for at-rest health payload snapshots.
    # If omitted, a deterministic key is derived from SECRET_KEY.
    ENCRYPTION_KEY: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:80", "http://localhost"]

    # Basic API abuse protection
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    AI_RETRY_ATTEMPTS: int = 2
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
