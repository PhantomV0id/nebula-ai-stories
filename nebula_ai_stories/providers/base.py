from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TextGenerationProvider(ABC):
    """Interface for future local text-generation backends."""

    @abstractmethod
    def generate_story_payloads(self, count: int) -> list[dict[str, Any]]:
        """Return deterministic or generated story dictionaries."""
