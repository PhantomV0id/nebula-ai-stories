from __future__ import annotations

import re

from nebula_ai_stories.models.story import StoryCandidate


_GENERIC_OBJECTS = {
    "ball",
    "cookie",
    "cracker",
    "shoe",
    "sock",
    "spoon",
    "toy",
}
_STOP_WORDS = {"a", "an", "the", "to", "for", "from", "with", "and", "of", "its", "their"}


class NoveltyEngine:
    """Deterministic V1 mechanic similarity; replaceable by embeddings later."""

    def __init__(self, duplicate_threshold: float = 0.72) -> None:
        self.duplicate_threshold = duplicate_threshold

    @staticmethod
    def _tokens(values: list[str]) -> set[str]:
        tokens: set[str] = set()
        for value in values:
            for raw in re.findall(r"[a-z0-9]+", value.lower()):
                if raw in _STOP_WORDS:
                    continue
                tokens.add("object" if raw in _GENERIC_OBJECTS else raw)
        return tokens

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left and not right:
            return 1.0
        union = left | right
        return len(left & right) / len(union) if union else 0.0

    def similarity(self, left: StoryCandidate, right: StoryCandidate) -> float:
        mechanics = self._jaccard(self._tokens(left.story_mechanics), self._tokens(right.story_mechanics))
        tags = self._jaccard(self._tokens(left.tags), self._tokens(right.tags))
        return round((mechanics * 0.85) + (tags * 0.15), 3)

    def are_duplicates(self, left: StoryCandidate, right: StoryCandidate) -> bool:
        return self.similarity(left, right) >= self.duplicate_threshold

    def novelty_score(self, candidate: StoryCandidate, existing: list[StoryCandidate]) -> float:
        if not existing:
            return 10.0
        highest_similarity = max(self.similarity(candidate, other) for other in existing)
        return round(max(0.0, min(10.0, (1.0 - highest_similarity) * 10.0)), 2)

    def filter_duplicates(self, candidates: list[StoryCandidate]) -> list[StoryCandidate]:
        unique: list[StoryCandidate] = []
        for candidate in candidates:
            if not any(self.are_duplicates(candidate, accepted) for accepted in unique):
                unique.append(candidate)
        return unique

