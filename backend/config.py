import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database - Using SQLite for simplicity
    database_url: str = "sqlite:///./selfheal.db"
    
    # Use in-memory event bus instead of Redis
    use_redis: bool = False
    redis_url: str = "redis://localhost:6379"
    
    # API Keys
    morph_api_key: str = "your_morph_api_key_here"
    openai_api_key: str = "your_openai_api_key_here"
    
    # App Settings
    environment: str = "development"
    secret_key: str = "your-secret-key-here-change-in-production"
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Healing Settings
    max_patch_size_lines: int = 30
    max_files_per_patch: int = 2
    allowed_file_patterns: List[str] = [
        "services/catalog_sync.*",
        "mappings/policy_fields.*",
        "handlers/return_policy.*"
    ]
    forbidden_file_patterns: List[str] = [
        "*.env",
        "config/*",
        "secrets/*",
        "infrastructure/*"
    ]
    
    class Config:
        env_file = ".env"

settings = Settings() 