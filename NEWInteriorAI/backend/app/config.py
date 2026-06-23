from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "InteriorAI"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql://admin:localpass@localhost:5432/interiorai"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    # AI — Claude
    anthropic_api_key: str = ""

    # AI — OpenAI
    openai_api_key: str = ""

    # Vector DB — Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_preferences: str = "user_preferences"
    qdrant_collection_knowledge: str = "design_knowledge"

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = "interiorai-uploads"
    aws_region: str = "eu-west-1"

    # Cloudinary
    cloudinary_url: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "https://yourdomain.com",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
