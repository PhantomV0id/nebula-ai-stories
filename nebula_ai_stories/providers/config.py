from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ProviderType = Literal["mock", "lm_studio", "ollama"]

DEFAULT_BASE_URLS: dict[str, str] = {
    "mock": "",
    "lm_studio": "http://127.0.0.1:1234",
    "ollama": "http://127.0.0.1:11434",
}


@dataclass(slots=True)
class ProviderConfig:
    provider_type: ProviderType | str = "mock"
    base_url: str = ""
    model: str = ""
    timeout_seconds: float = 120.0
    temperature: float = 0.8
    max_tokens: int | None = 4096

    def __post_init__(self) -> None:
        provider_type = str(self.provider_type).strip().lower()
        if provider_type not in DEFAULT_BASE_URLS:
            raise ValueError("provider_type must be one of: mock, lm_studio, ollama")
        self.provider_type = provider_type

        self.base_url = self.base_url.strip().rstrip("/") or DEFAULT_BASE_URLS[provider_type]
        self.model = self.model.strip()
        self.timeout_seconds = float(self.timeout_seconds)
        self.temperature = float(self.temperature)

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0 and 2")
        if self.max_tokens is not None:
            self.max_tokens = int(self.max_tokens)
            if self.max_tokens <= 0:
                raise ValueError("max_tokens must be greater than 0 when provided")
