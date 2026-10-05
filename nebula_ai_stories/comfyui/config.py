from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ComfyUIConfig:
    base_url: str = "http://127.0.0.1:8188"
    timeout_seconds: float = 600.0
    poll_interval_seconds: float = 1.0
    workflow_path: Path | None = None
    binding_profile_path: Path | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.base_url, str):
            raise ValueError("base_url must be a string")
        self.base_url = self.base_url.strip().rstrip("/") or "http://127.0.0.1:8188"
        self.timeout_seconds = float(self.timeout_seconds)
        self.poll_interval_seconds = float(self.poll_interval_seconds)
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than 0")
        if self.workflow_path is not None:
            self.workflow_path = Path(self.workflow_path)
        if self.binding_profile_path is not None:
            self.binding_profile_path = Path(self.binding_profile_path)
