from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Chat & Agent Studio"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Storage & Paths
    SQLITE_DB_PATH: str = "/opt/assistant-core/data/assistant.db"
    WORKSPACE_ROOT: str = "/opt/chat-app"

    # Персона, читаемая из таблиц общей БД (YAML читает только assistant-core)
    PERSONA_ID: str = "popov-da-default"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
