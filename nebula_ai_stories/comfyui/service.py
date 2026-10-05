from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from nebula_ai_stories.comfyui.artifacts import discover_artifacts
from nebula_ai_stories.comfyui.bindings import patch_workflow
from nebula_ai_stories.comfyui.errors import ComfyUIError, RenderExecutionError, WorkflowBindingError
from nebula_ai_stories.comfyui.models import BindingProfile, RenderArtifact, RenderResult, UploadedImage
from nebula_ai_stories.models.shot import Shot


class RenderClient(Protocol):
    def upload_image(self, path: Path) -> UploadedImage: ...

    def queue_workflow(self, workflow: dict[str, Any]) -> str: ...

    def wait_for_completion(self, prompt_id: str) -> dict[str, Any]: ...

    def download_artifact(self, artifact: RenderArtifact, destination: Path) -> RenderArtifact: ...


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_segment(value: str, fallback: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-")
    return safe or fallback


class ComfyRenderService:
    def __init__(self, client: RenderClient, output_root: str | Path = "outputs") -> None:
        self.client = client
        self.output_root = Path(output_root)

    def render_shot(
        self,
        shot: Shot,
        story_id: str,
        workflow: dict[str, Any],
        profile: BindingProfile,
        input_image_path: str | Path,
        *,
        negative_prompt: str | None = None,
        seed: int | None = None,
        output_prefix: str | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> RenderResult:
        if "input_image" not in profile.bindings:
            raise WorkflowBindingError("Binding profile requires an input_image binding for single-shot I2V rendering")

        def status(message: str) -> None:
            if on_status is not None:
                on_status(message)

        started_at = _utc_now_iso()
        keyframe = Path(input_image_path)
        status("Uploading keyframe...")
        uploaded = self.client.upload_image(keyframe)

        values: dict[str, Any] = {
            "image_prompt": shot.image_prompt,
            "motion_prompt": shot.motion_prompt,
            "input_image": uploaded.comfyui_path,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "output_prefix": output_prefix,
        }
        patched = patch_workflow(workflow, profile, values)

        status("Queuing workflow...")
        prompt_id = self.client.queue_workflow(patched)
        status("Rendering...")
        history_entry = self.client.wait_for_completion(prompt_id)
        artifacts = discover_artifacts(history_entry)
        if not artifacts:
            raise RenderExecutionError(f"ComfyUI prompt {prompt_id} completed but produced no downloadable artifacts")

        story_dir = _safe_segment(story_id, "story")
        output_dir = self.output_root / story_dir / f"shot-{shot.shot_index:03d}"
        status("Downloading output...")
        downloaded = [self.client.download_artifact(artifact, output_dir) for artifact in artifacts]
        status("Complete")
        return RenderResult(
            prompt_id=prompt_id,
            shot_index=shot.shot_index,
            status="complete",
            artifacts=downloaded,
            started_at=started_at,
            completed_at=_utc_now_iso(),
        )
