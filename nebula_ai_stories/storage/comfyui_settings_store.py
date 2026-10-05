from __future__ import annotations

import json
from pathlib import Path

from nebula_ai_stories.comfyui.config import ComfyUIConfig


DEFAULT_COMFYUI_SETTINGS_PATH = Path("data") / "comfyui_settings.json"


class ComfyUISettingsStore:
    def __init__(self, path: str | Path = DEFAULT_COMFYUI_SETTINGS_PATH) -> None:
        self.path = Path(path)

    def load(self) -> ComfyUIConfig:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return ComfyUIConfig()
            workflow = raw.get("workflow_path") or None
            profile = raw.get("binding_profile_path") or None
            return ComfyUIConfig(
                base_url=raw.get("base_url", "http://127.0.0.1:8188"),
                timeout_seconds=raw.get("timeout_seconds", 600),
                poll_interval_seconds=raw.get("poll_interval_seconds", 1),
                workflow_path=Path(workflow) if workflow else None,
                binding_profile_path=Path(profile) if profile else None,
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return ComfyUIConfig()

    def save(self, config: ComfyUIConfig) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "base_url": config.base_url,
            "timeout_seconds": config.timeout_seconds,
            "poll_interval_seconds": config.poll_interval_seconds,
            "workflow_path": str(config.workflow_path) if config.workflow_path else "",
            "binding_profile_path": str(config.binding_profile_path) if config.binding_profile_path else "",
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.path
