from typing import List

from pydantic.v1 import BaseSettings
from pydantic_settings import SettingsConfigDict


class Setting(BaseSettings):
    """Global APP Config"""
    APP_NAME: str = "AI Smart Chatbot"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI Smart Chatbot Backend API"

    """API Configuration"""
    API_ENDPOINT: str = "http://localhost:8088"
    API_PATH: str = "/api/v1"

    """Connection to MySQL Server"""
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "ai_chatbot"

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    """ChromaDB Configuration"""
    CHROMA_PATH: str = "E:/work/ai-chatbot/modules/chroma_db"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    COLLECTION_NAME: str = "chatbot"

    """Setup Allow Origins for FE"""
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    """Config Encode Algorithm"""
    SECRET_KEY: str = "ai_chatbot_pancharm"
    ALGORITHM: str = "HS512"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 30

    """Config Redis"""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    """Config Kafka"""

    """Config MinIO"""
    MINIO_ENDPOINT: str = "localhost:9002"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "123456789"
    MINIO_USE_SSL: bool = False

    """Ollama Model Config"""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    """Config LLM Models"""
    HF_TOKEN: str = ""

    """Facebook API Config"""
    PAGE_ID: str = ""
    PAGE_ACCESS_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Setting()