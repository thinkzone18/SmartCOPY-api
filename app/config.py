from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    MONGO_URI: str
    DB_NAME: str
    COLLECTION_NAME: str

    # API Keys
    ADMIN_API_KEY: str
    GUMROAD_SECRET: str | None = None

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Email (new)
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASS: str
    EMAIL_SENDER_NAME: str = "ThinkZone Support"

    class Config:
        env_file = ".env"

settings = Settings()

