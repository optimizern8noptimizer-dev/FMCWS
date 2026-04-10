from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "FMCWS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./fmcws.db"
    SECRET_KEY: str = "fmcws-secret-change-in-production-32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Service-to-service API key (банк → FMCWS)
    API_KEY: str = "demo-fmcws-api-key-change-in-prod"

    # Webhook для уведомления банковского backend об алертах
    BANK_WEBHOOK_URL: str = ""

    # Пороги оповещения клиента
    WARN_THRESHOLD_MEDIUM: int = 31
    WARN_THRESHOLD_HIGH: int = 61
    WARN_THRESHOLD_CRITICAL: int = 86

    class Config:
        env_file = ".env"


settings = Settings()
