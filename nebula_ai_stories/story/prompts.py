from __future__ import annotations


IMAGE_STYLE = (
    "Realistic casual smartphone video frame, ordinary believable environment, natural household or outdoor lighting, "
    "slightly imperfect candid framing, realistic proportions and textures"
)

MOTION_STYLE = (
    "Natural body movement, simple readable action, restrained handheld phone motion, minimal camera movement, "
    "no dramatic zooms or cinematic sweeps"
)


def build_image_prompt(visual_description: str, camera: str) -> str:
    return f"{IMAGE_STYLE}. Scene: {visual_description}. Camera: {camera}."


def build_motion_prompt(action: str) -> str:
    return f"{MOTION_STYLE}. Main movement: {action}."
