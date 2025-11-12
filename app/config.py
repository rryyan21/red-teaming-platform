"""
Configuration management using Pydantic Settings.

This module centralizes all configuration from environment variables.
It validates required settings and provides type-safe access to config values.

Why Pydantic Settings?
- Automatic validation of environment variables
- Type conversion (strings to ints, etc.)
- Single source of truth for configuration
- Easy to test by overriding settings
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        llm_provider: Which LLM provider to use (default: "openai")
        llm_api_key: API key for the LLM provider (required)
        database_url: SQLite database connection string
        secret_key: Secret key for session management (future use)
    """
    llm_provider: str = "openai"
    llm_api_key: str
    database_url: str = "sqlite:///./red_teaming.db"
    secret_key: str = "dev-secret-key-change-in-production"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create a global settings instance
# This will be imported by other modules
settings = Settings()

