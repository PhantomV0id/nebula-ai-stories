from __future__ import annotations

from abc import abstractmethod
from typing import Any

from nebula_ai_stories.providers.base import TextGenerationProvider
from nebula_ai_stories.providers.errors import ProviderError, ProviderGenerationError, ProviderOutputError
from nebula_ai_stories.providers.json_extract import extract_story_payloads
from nebula_ai_stories.story.generation_prompt import build_story_generation_prompt, build_story_repair_prompt


class RepairingLocalProvider(TextGenerationProvider):
    """Shared exactly-once repair behavior for local chat providers."""

    @abstractmethod
    def _request_content(self, user_prompt: str) -> str:
        """Send one chat request and return assistant text."""

    def generate_story_payloads(self, count: int) -> list[dict[str, Any]]:
        if count < 1:
            raise ValueError("count must be at least 1")
        try:
            first_content = self._request_content(build_story_generation_prompt(count))
            return extract_story_payloads(first_content, count)
        except ProviderOutputError as first_error:
            repair_prompt = build_story_repair_prompt(count, str(first_error))

        try:
            repaired_content = self._request_content(repair_prompt)
            return extract_story_payloads(repaired_content, count)
        except ProviderError as exc:
            raise ProviderGenerationError(f"Story generation repair failed: {exc}") from exc
