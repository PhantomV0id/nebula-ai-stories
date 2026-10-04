from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from nebula_ai_stories.providers.config import ProviderConfig
from nebula_ai_stories.providers.errors import ProviderError, ProviderResponseError
from nebula_ai_stories.providers.http import get_json


GetFn = Callable[[str, float], dict[str, Any]]


@dataclass(slots=True, frozen=True)
class ProviderHealth:
    available: bool
    message: str
    models: list[str]


def _lm_studio_models(response: dict[str, Any]) -> list[str]:
    data = response.get("data", [])
    if not isinstance(data, list):
        raise ProviderResponseError("LM Studio models response has invalid 'data'")
    return [item["id"].strip() for item in data if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip()]


def _ollama_models(response: dict[str, Any]) -> list[str]:
    data = response.get("models", [])
    if not isinstance(data, list):
        raise ProviderResponseError("Ollama models response has invalid 'models'")
    models: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model")
        if isinstance(name, str) and name.strip():
            models.append(name.strip())
    return models


def check_provider_health(config: ProviderConfig, get_fn: GetFn = get_json) -> ProviderHealth:
    if config.provider_type == "mock":
        return ProviderHealth(True, "Mock Provider: Ready (offline)", [])

    display = "LM Studio" if config.provider_type == "lm_studio" else "Ollama"
    endpoint = "/v1/models" if config.provider_type == "lm_studio" else "/api/tags"
    try:
        response = get_fn(f"{config.base_url}{endpoint}", config.timeout_seconds)
        models = _lm_studio_models(response) if config.provider_type == "lm_studio" else _ollama_models(response)
    except ProviderError as exc:
        return ProviderHealth(False, f"{display} unavailable: {exc}", [])
    return ProviderHealth(True, f"{display}: Connected", models)
