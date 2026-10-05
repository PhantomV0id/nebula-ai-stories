from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nebula_ai_stories.providers.config import ProviderConfig
from nebula_ai_stories.providers.errors import ProviderConfigurationError, ProviderOutputError
from nebula_ai_stories.providers.http import post_json
from nebula_ai_stories.providers.local_provider import RepairingLocalProvider
from nebula_ai_stories.story.generation_prompt import SYSTEM_PROMPT


RequestFn = Callable[[str, dict[str, Any], float], dict[str, Any]]


class LMStudioProvider(RepairingLocalProvider):
    def __init__(self, config: ProviderConfig, request_fn: RequestFn = post_json) -> None:
        if config.provider_type != "lm_studio":
            raise ProviderConfigurationError("LMStudioProvider requires provider_type='lm_studio'")
        if not config.model:
            raise ProviderConfigurationError("LM Studio model must be configured")
        self.config = config
        self.request_fn = request_fn

    def _request_content(self, user_prompt: str) -> str:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "stream": False,
        }
        if self.config.max_tokens is not None:
            body["max_tokens"] = self.config.max_tokens

        response = self.request_fn(
            f"{self.config.base_url}/v1/chat/completions",
            body,
            self.config.timeout_seconds,
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderOutputError("LM Studio returned a malformed chat completion response") from exc
        if not isinstance(content, str):
            raise ProviderOutputError("LM Studio returned non-text model output")
        return content
