from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any


@dataclass(slots=True, frozen=True)
class WorkflowBinding:
    node_id: str
    input_name: str

    def __post_init__(self) -> None:
        if not str(self.node_id).strip():
            raise ValueError("node_id must be non-empty")
        if not self.input_name.strip():
            raise ValueError("input_name must be non-empty")
        object.__setattr__(self, "node_id", str(self.node_id).strip())
        object.__setattr__(self, "input_name", self.input_name.strip())


@dataclass(slots=True, frozen=True)
class BindingProfile:
    name: str
    bindings: dict[str, WorkflowBinding]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("binding profile name must be non-empty")
        object.__setattr__(self, "name", self.name.strip())


@dataclass(slots=True, frozen=True)
class ComfyUIHealth:
    available: bool
    message: str
    system_info: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class UploadedImage:
    filename: str
    subfolder: str = ""
    type: str = "input"

    @property
    def comfyui_path(self) -> str:
        if self.subfolder.strip():
            return str(PurePosixPath(self.subfolder.strip().replace("\\", "/")) / self.filename)
        return self.filename


@dataclass(slots=True, frozen=True)
class RenderArtifact:
    filename: str
    subfolder: str
    type: str
    node_id: str
    local_path: Path | None = None

    @property
    def extension(self) -> str:
        return Path(self.filename).suffix.lower()


@dataclass(slots=True, frozen=True)
class RenderResult:
    prompt_id: str
    shot_index: int
    status: str
    artifacts: list[RenderArtifact]
    started_at: str
    completed_at: str
