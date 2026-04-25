from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ALLOWED_ORIGIN: str = "http://localhost:3000"
    ADMIN_TOKEN: str = "changeme"
    DATABASE_URL: str = "postgresql+asyncpg://devynn:devynn@localhost/devynn"
    REDIS_URL: str = "redis://localhost:6379/0"
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_AUDIO: str = "devynn-audio"
    S3_BUCKET_MODELS: str = "devynn-models"
    MODEL_PATH: str = ""
    WHISPER_MODEL_SIZE: str = "base"
    MODEL_VERSION: str = "mistral-v1"


settings = Settings()
