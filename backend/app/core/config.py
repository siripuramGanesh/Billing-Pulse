from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BillingPulse"
    DEBUG: bool = False
    APP_ENV: str = "development"  # development | staging | production

    # Phase 7: encryption at rest for sensitive claim fields (notes, denial_reason)
    ENCRYPT_SENSITIVE_FIELDS: bool = False
    ENCRYPTION_KEY: str = ""  # 32-byte URL-safe base64 key for Fernet; generate with cryptography.fernet.Fernet.generate_key()

    # Phase 7: error tracking (optional)
    SENTRY_DSN: str = ""

    # Database
    DATABASE_URL: str = "postgresql://billingpulse:billingpulse_dev@localhost:5432/billingpulse"

    # Auth
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Voice AI (Phase 2 - set in .env for real usage)
    VAPI_API_KEY: str = ""
    VAPI_ASSISTANT_ID: str = ""  # Saved assistant ID from Vapi dashboard
    VAPI_PHONE_NUMBER_ID: str = ""  # Phone number ID from Vapi (Twilio-imported)
    BLAND_AI_API_KEY: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # LLM (Phase 3 - agentic AI)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""

    # Redis (Phase 4 - Celery broker)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Call queue (Phase 4)
    CALL_RATE_LIMIT_PER_PAYER: int = 2  # max calls per payer per window
    CALL_RATE_LIMIT_WINDOW: int = 300  # 5 minutes

    # Email (claimer notifications)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    MAIL_FROM_EMAIL: str = "noreply@billingpulse.local"
    MAIL_FROM_NAME: str = "BillingPulse"
    USE_MCP_EMAIL: bool = False  # if True, send email via MCP server (spawned subprocess) instead of direct SMTP

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
