from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _clean_strings(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


@dataclass(slots=True)
class StoryCandidate:
    id: str
    title: str
    premise: str
    hook: str
    problem: str
    action: str
    twist: str
    payoff: str
    emotion: str
    estimated_duration_seconds: float
    dialogue_lines: list[str] = field(default_factory=list)
    visual_requirements: list[str] = field(default_factory=list)
    generation_difficulty: str = "moderate"
    story_mechanics: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        required = (
            "id",
            "title",
            "premise",
            "hook",
            "problem",
            "action",
            "twist",
            "payoff",
            "emotion",
            "generation_difficulty",
        )
        for name in required:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
            setattr(self, name, value.strip())

        self.estimated_duration_seconds = float(self.estimated_duration_seconds)
        if not 8.0 <= self.estimated_duration_seconds <= 15.0:
            raise ValueError("estimated_duration_seconds must be between 8 and 15 seconds")

        self.generation_difficulty = self.generation_difficulty.lower()
        if self.generation_difficulty not in {"easy", "moderate", "hard"}:
            raise ValueError("generation_difficulty must be easy, moderate, or hard")

        self.dialogue_lines = _clean_strings(self.dialogue_lines)
        self.visual_requirements = _clean_strings(self.visual_requirements)
        self.story_mechanics = _clean_strings(self.story_mechanics)
        self.tags = _clean_strings(self.tags)
        if not self.story_mechanics:
            raise ValueError("story_mechanics must contain at least one mechanic")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoryCandidate":
        return cls(**data)


@dataclass(slots=True)
class StoryScore:
    hook_strength: float = 0.0
    visual_clarity: float = 0.0
    conflict_strength: float = 0.0
    payoff_strength: float = 0.0
    emotional_strength: float = 0.0
    generation_feasibility: float = 0.0
    novelty: float = 0.0
    overall_score: float = 0.0
    rejected: bool = False
    rejection_reason: str | None = None

    SCORE_FIELDS = (
        "hook_strength",
        "visual_clarity",
        "conflict_strength",
        "payoff_strength",
        "emotional_strength",
        "generation_feasibility",
        "novelty",
        "overall_score",
    )

    def __post_init__(self) -> None:
        for field_name in self.SCORE_FIELDS:
            value = float(getattr(self, field_name))
            setattr(self, field_name, round(max(0.0, min(10.0, value)), 2))
        if self.rejection_reason is not None:
            self.rejection_reason = self.rejection_reason.strip() or None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoryScore":
        return cls(**data)
