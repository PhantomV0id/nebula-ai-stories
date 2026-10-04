from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Shot:
    shot_index: int
    duration_seconds: float
    story_function: str
    visual_description: str
    image_prompt: str
    motion_prompt: str
    camera: str
    characters: list[str] = field(default_factory=list)
    props: list[str] = field(default_factory=list)
    continuity_notes: str = ""

    def __post_init__(self) -> None:
        if self.shot_index < 1:
            raise ValueError("shot_index must start at 1")
        self.duration_seconds = float(self.duration_seconds)
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        for name in ("story_function", "visual_description", "image_prompt", "motion_prompt", "camera"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
            setattr(self, name, value.strip())
        self.characters = [value.strip() for value in self.characters if value.strip()]
        self.props = [value.strip() for value in self.props if value.strip()]
        self.continuity_notes = self.continuity_notes.strip()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Shot":
        return cls(**data)

