from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from nebula_ai_stories.providers.config import ProviderConfig


DEFAULT_SETTINGS_PATH = Path("data") / "provider_settings.json"


class SettingsStore:
    def __init__(self, path: str | Path = DEFAULT_SETTINGS_PATH) -> None:
        self.path = Path(path)

    def load(self) -> ProviderConfig:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return ProviderConfig()
            allowed = {"provider_type", "base_url", "model", "timeout_seconds", "temperature", "max_tokens"}
            return ProviderConfig(**{key: raw[key] for key in allowed if key in raw})
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return ProviderConfig()

    def save(self, config: ProviderConfig) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
        return self.path
