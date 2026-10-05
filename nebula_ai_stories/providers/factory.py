from __future__ import annotations

from nebula_ai_stories.providers.base import TextGenerationProvider
from nebula_ai_stories.providers.config import ProviderConfig
from nebula_ai_stories.providers.errors import ProviderConfigurationError
from nebula_ai_stories.providers.lm_studio import LMStudioProvider
from nebula_ai_stories.providers.mock_provider import MockProvider
from nebula_ai_stories.providers.ollama import OllamaProvider


def create_provider(config: ProviderConfig) -> TextGenerationProvider:
    if config.provider_type == "mock":
        return MockProvider()
    if config.provider_type == "lm_studio":
        return LMStudioProvider(config)
    if config.provider_type == "ollama":
        return OllamaProvider(config)
    raise ProviderConfigurationError(f"Unsupported provider type: {config.provider_type}")
