from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    TELEGRAM_TOKEN: str
    MOODLE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()