from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    APP_NAME: str = "Pancharm AI Retail Consultant"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Multi-Agent System for Feng Shui Jewelry Retail Consultation"

    API_ENDPOINT: str = "http://localhost:8088"
    API_PATH: str = "/api/v1"

    # MySQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "ai_chatbot"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # PostgreSQL (primary physical database)
    PG_HOST: str = "localhost"
    PG_PORT: int = 5432
    PG_NAME: str = "ai-chatbot"
    PG_USER: str = "admin"
    PG_PASSWORD: str = "123456789"
    PG_POOL_SIZE: int = 10
    PG_MAX_OVERFLOW: int = 20

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PATH: str = "./chroma_db"

    # LLM — Anthropic (primary) + OpenAI (embeddings)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL_PRIMARY: str = "claude-sonnet-4-6"    # Orchestrator + Synth Agent
    ANTHROPIC_MODEL_FAST: str = "claude-haiku-4-5-20251001"  # KR Agent + Psych Agent
    OPENAI_API_KEY: str = ""

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # Auth
    SECRET_KEY: str = "pancharm_mas_secret"
    ALGORITHM: str = "HS512"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9002"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "123456789"
    MINIO_USE_SSL: bool = False

    # LangSmith tracing (optional)
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "pancharm-mas"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_WEBHOOK_BASE_URL: str = ""   # https://yourdomain.com | ngrok URL khi dev

    # Facebook Messenger
    MESSENGER_PAGE_ACCESS_TOKEN: str = ""
    MESSENGER_APP_SECRET: str = ""        # để verify X-Hub-Signature-256
    MESSENGER_VERIFY_TOKEN: str = ""      # để verify webhook khi setup trên Facebook

    # Zalo OA
    ZALO_OA_ACCESS_TOKEN: str = ""
    ZALO_APP_SECRET: str = ""             # để verify MAC signature

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CLIENT_ID: str = "pancharm-mas"
    KAFKA_CONSUMER_GROUP: str = "pancharm-mas"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Setting()
