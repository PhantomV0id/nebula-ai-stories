from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nebula_ai_stories.providers.base import TextGenerationProvider
from nebula_ai_stories.providers.config import ProviderConfig
from nebula_ai_stories.providers.errors import ProviderConfigurationError, ProviderOutputError
from nebula_ai_stories.providers.http import post_json
from nebula_ai_stories.providers.local_provider import RepairingLocalProvider
from nebula_ai_stories.story.generation_prompt import SYSTEM_PROMPT


RequestFn = Callable[[str, dict[str, Any], float], dict[str, Any]]


class OllamaProvider(RepairingLocalProvider):
    def __init__(self, config: ProviderConfig, request_fn: RequestFn = post_json) -> None:
        if config.provider_type != "ollama":
            raise ProviderConfigurationError("OllamaProvider requires provider_type='ollama'")
        if not config.model:
            raise ProviderConfigurationError("Ollama model must be configured")
        self.config = config
        self.request_fn = request_fn

    def _request_content(self, user_prompt: str) -> str:
        options: dict[str, Any] = {"temperature": self.config.temperature}
        if self.config.max_tokens is not None:
            options["num_predict"] = self.config.max_tokens
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "options": options,
        }
        response = self.request_fn(
            f"{self.config.base_url}/api/chat",
            body,
            self.config.timeout_seconds,
        )
        try:
            content = response["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise ProviderOutputError("Ollama returned a malformed chat response") from exc
        if not isinstance(content, str):
            raise ProviderOutputError("Ollama returned non-text model output")
        return content
