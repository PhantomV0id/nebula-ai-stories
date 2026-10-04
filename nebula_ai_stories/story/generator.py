from __future__ import annotations

from nebula_ai_stories.models.story import StoryCandidate
from nebula_ai_stories.providers.base import TextGenerationProvider


class StoryGenerator:
    def __init__(self, provider: TextGenerationProvider) -> None:
        self.provider = provider

    def generate_candidates(self, count: int = 20) -> list[StoryCandidate]:
        if count < 1:
            raise ValueError("count must be at least 1")
        payloads = self.provider.generate_story_payloads(count)
        if len(payloads) != count:
            raise ValueError(f"provider returned {len(payloads)} stories; expected {count}")
        return [StoryCandidate.from_dict(payload) for payload in payloads]

