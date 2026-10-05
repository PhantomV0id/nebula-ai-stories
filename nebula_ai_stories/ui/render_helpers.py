from __future__ import annotations

from pathlib import Path

from nebula_ai_stories.comfyui.client import SUPPORTED_IMAGE_EXTENSIONS
from nebula_ai_stories.comfyui.config import ComfyUIConfig
from nebula_ai_stories.models.shot import Shot


def build_comfyui_config(
    base_url: str,
    timeout_text: str,
    poll_interval_text: str,
    workflow_path: str | Path | None,
    binding_profile_path: str | Path | None,
) -> ComfyUIConfig:
    workflow = Path(workflow_path) if workflow_path else None
    profile = Path(binding_profile_path) if binding_profile_path else None
    return ComfyUIConfig(
        base_url=base_url,
        timeout_seconds=float(timeout_text),
        poll_interval_seconds=float(poll_interval_text),
        workflow_path=workflow,
        binding_profile_path=profile,
    )


def shot_choices(shots: list[Shot]) -> tuple[str, ...]:
    return tuple(str(shot.shot_index) for shot in shots)


def selected_shot(shots: list[Shot], selection: str) -> Shot:
    try:
        shot_index = int(selection)
    except ValueError as exc:
        raise ValueError("Select a shot before rendering") from exc
    for shot in shots:
        if shot.shot_index == shot_index:
            return shot
    raise ValueError(f"Selected shot {shot_index} is not present in the current shot plan")


def format_shot_for_render(shot: Shot) -> str:
    return "\n".join(
        [
            f"SHOT {shot.shot_index} — {shot.duration_seconds:.1f}s — {shot.story_function}",
            "",
            f"Image prompt:\n{shot.image_prompt}",
            "",
            f"Motion prompt:\n{shot.motion_prompt}",
        ]
    )


def validate_keyframe_path(path: str | Path) -> Path:
    image_path = Path(path)
    if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError("Keyframe must be PNG, JPG, JPEG, or WEBP")
    if not image_path.is_file():
        raise ValueError(f"Keyframe image does not exist: {image_path}")
    return image_path
