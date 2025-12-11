"""
Multi-model LLM provider abstraction layer.
Supports OpenAI, Anthropic Claude, and Google Gemini.
"""

from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import Settings
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """Get the configured LLM model instance."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

    def get_model(self) -> BaseChatModel:
        """Get OpenAI ChatGPT model."""
        return ChatOpenAI(
            api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
            streaming=True,
        )

    def get_provider_name(self) -> str:
        return "OpenAI"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")

    def get_model(self) -> BaseChatModel:
        """Get Anthropic Claude model."""
        return ChatAnthropic(
            api_key=self.settings.anthropic_api_key,
            model=self.settings.anthropic_model,
            temperature=self.settings.anthropic_temperature,
            streaming=True,
        )

    def get_provider_name(self) -> str:
        return "Anthropic"


class GoogleProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.google_api_key:
            raise ValueError("Google API key not configured")

    def get_model(self) -> BaseChatModel:
        """Get Google Gemini model."""
        return ChatGoogleGenerativeAI(
            google_api_key=self.settings.google_api_key,
            model=self.settings.google_model,
            temperature=self.settings.google_temperature,
            streaming=True,
        )

    def get_provider_name(self) -> str:
        return "Google"


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    _providers: Dict[str, type[LLMProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
    }

    @classmethod
    def create_provider(
        cls, provider_name: str, settings: Settings
    ) -> LLMProvider:
        """Create an LLM provider instance based on the provider name."""
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Available providers: {list(cls._providers.keys())}"
            )

        try:
            return provider_class(settings)
        except Exception as e:
            logger.error(f"Failed to initialize {provider_name} provider: {e}")
            raise

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())


def get_llm_model(settings: Optional[Settings] = None) -> BaseChatModel:
    """
    Get the configured LLM model.

    Args:
        settings: Application settings. If None, will load from environment.

    Returns:
        Configured LangChain chat model instance.
    """
    from src.config import get_settings

    if settings is None:
        settings = get_settings()

    provider = LLMProviderFactory.create_provider(settings.llm_provider, settings)
    logger.info(
        f"Initialized {provider.get_provider_name()} LLM provider "
        f"with model: {getattr(settings, f'{settings.llm_provider}_model')}"
    )

    return provider.get_model()
