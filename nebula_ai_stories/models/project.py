from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from nebula_ai_stories.models.shot import Shot
from nebula_ai_stories.models.story import StoryCandidate, StoryScore


CURRENT_SCHEMA_VERSION = 1


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class StoryProject:
    schema_version: int = CURRENT_SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    generated_candidates: list[StoryCandidate] = field(default_factory=list)
    scores: dict[str, StoryScore] = field(default_factory=dict)
    selected_story: StoryCandidate | None = None
    shot_plan: list[Shot] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "generated_candidates": [candidate.to_dict() for candidate in self.generated_candidates],
            "scores": {story_id: score.to_dict() for story_id, score in self.scores.items()},
            "selected_story": self.selected_story.to_dict() if self.selected_story else None,
            "shot_plan": [shot.to_dict() for shot in self.shot_plan],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoryProject":
        required = {
            "schema_version",
            "created_at",
            "updated_at",
            "generated_candidates",
            "scores",
            "selected_story",
            "shot_plan",
        }
        missing = required - data.keys()
        if missing:
            raise ValueError(f"missing required project data: {', '.join(sorted(missing))}")
        if data["schema_version"] != CURRENT_SCHEMA_VERSION:
            raise ValueError(f"unsupported schema version: {data['schema_version']}")

        selected_data = data["selected_story"]
        return cls(
            schema_version=int(data["schema_version"]),
            created_at=str(data["created_at"]),
            updated_at=str(data["updated_at"]),
            generated_candidates=[StoryCandidate.from_dict(item) for item in data["generated_candidates"]],
            scores={story_id: StoryScore.from_dict(score) for story_id, score in data["scores"].items()},
            selected_story=StoryCandidate.from_dict(selected_data) if selected_data else None,
            shot_plan=[Shot.from_dict(item) for item in data["shot_plan"]],
        )

