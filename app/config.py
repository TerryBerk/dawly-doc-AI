"""Application configuration"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # KAG Configuration
    KAG_PROJECT_NAME: str = "dawly_docs"
    KAG_LANGUAGE: str = "en"
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "dawly_kag"
    POSTGRES_USER: str = "kaguser"
    POSTGRES_PASSWORD: str = "changeme"
    
    # LLM Configuration
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4"
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://dawly.io"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
