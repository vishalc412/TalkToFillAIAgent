"""
Configuration management for the AI Voice Form Filling Agent.
"""

from pydantic_settings import BaseSettings
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Provider Configuration
    llm_provider: Literal["openai", "anthropic", "google"] = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.7

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_temperature: float = 0.7

    # Google Gemini
    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash-exp"
    google_temperature: float = 0.7

    # Speech-to-Text
    stt_provider: Literal["openai", "google", "whisper-local"] = "openai"
    stt_language: str = "en-US"

    # Text-to-Speech
    tts_provider: Literal["openai", "google", "gtts"] = "openai"
    tts_voice: str = "alloy"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Application Settings
    max_conversation_history: int = 20
    session_timeout_minutes: int = 30
    enable_logging: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
