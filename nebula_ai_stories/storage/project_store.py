from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nebula_ai_stories.models.project import StoryProject


class ProjectLoadError(ValueError):
    """A user-facing project loading error that callers can handle safely."""


class ProjectStore:
    def save(self, project: StoryProject, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        project.touch()
        destination.write_text(json.dumps(project.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return destination

    def load(self, path: str | Path) -> StoryProject:
        source = Path(path)
        try:
            raw: Any = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ProjectLoadError(f"project file was not found: {source}") from exc
        except json.JSONDecodeError as exc:
            raise ProjectLoadError(f"project JSON is malformed: {exc.msg}") from exc
        except OSError as exc:
            raise ProjectLoadError(f"project file could not be read: {exc}") from exc

        if not isinstance(raw, dict):
            raise ProjectLoadError("project JSON must contain an object at the top level")
        try:
            return StoryProject.from_dict(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectLoadError(str(exc)) from exc
