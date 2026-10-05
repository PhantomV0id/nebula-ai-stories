from __future__ import annotations

from pathlib import Path

import pytest

from nebula_ai_stories.comfyui.config import ComfyUIConfig
from nebula_ai_stories.models.project import StoryProject
from nebula_ai_stories.models.shot import Shot
from nebula_ai_stories.models.story import StoryCandidate
from nebula_ai_stories.ui.app import NebulaStoriesApp
from nebula_ai_stories.ui.render_helpers import (
    build_comfyui_config,
    format_shot_for_render,
    selected_shot,
    shot_choices,
    validate_keyframe_path,
)


def make_shot(index: int) -> Shot:
    return Shot(
        shot_index=index,
        duration_seconds=4,
        story_function=f"Shot {index}",
        visual_description=f"Visual {index}",
        image_prompt=f"Image prompt {index}",
        motion_prompt=f"Motion prompt {index}",
        camera="handheld",
    )


def make_story(story_id: str) -> StoryCandidate:
    return StoryCandidate(
        id=story_id,
        title=f"Story {story_id}",
        premise="A small visual problem unfolds.",
        hook="Something starts to go wrong.",
        problem="An object is about to fall.",
        action="The character reacts.",
        twist="The reaction causes a surprise.",
        payoff="The problem resolves visually.",
        emotion="amused",
        estimated_duration_seconds=10,
        generation_difficulty="easy",
        story_mechanics=["cause and effect"],
    )


class FakeTree:
    def __init__(self, selected_id: str) -> None:
        self.selected_id = selected_id

    def selection(self) -> tuple[str, ...]:
        return (self.selected_id,)


class FakeText:
    def __init__(self) -> None:
        self.value = ""

    def configure(self, **_kwargs: object) -> None:
        pass

    def delete(self, *_args: object) -> None:
        self.value = ""

    def insert(self, _index: object, value: str) -> None:
        self.value = value


def test_build_comfyui_config_from_ui_strings() -> None:
    config = build_comfyui_config(
        "http://127.0.0.1:8188/",
        "300",
        "1.5",
        "workflow.json",
        "profile.json",
    )

    assert config == ComfyUIConfig(
        base_url="http://127.0.0.1:8188",
        timeout_seconds=300,
        poll_interval_seconds=1.5,
        workflow_path=Path("workflow.json"),
        binding_profile_path=Path("profile.json"),
    )


def test_shot_choices_and_selection_follow_real_shot_indexes() -> None:
    shots = [make_shot(1), make_shot(3)]

    assert shot_choices(shots) == ("1", "3")
    assert selected_shot(shots, "3").shot_index == 3


def test_selected_shot_rejects_missing_selection() -> None:
    with pytest.raises(ValueError, match="shot"):
        selected_shot([make_shot(1)], "2")


def test_render_shot_format_contains_separate_image_and_motion_prompts() -> None:
    text = format_shot_for_render(make_shot(2))

    assert "Image prompt 2" in text
    assert "Motion prompt 2" in text
    assert "Image prompt:" in text
    assert "Motion prompt:" in text


def test_validate_keyframe_accepts_supported_existing_image(tmp_path: Path) -> None:
    image = tmp_path / "frame.webp"
    image.write_bytes(b"image")

    assert validate_keyframe_path(image) == image


def test_validate_keyframe_rejects_unsupported_extension(tmp_path: Path) -> None:
    image = tmp_path / "frame.bmp"
    image.write_bytes(b"image")

    with pytest.raises(ValueError, match="PNG"):
        validate_keyframe_path(image)


def test_selecting_different_story_invalidates_existing_shot_plan() -> None:
    story_a = make_story("story-a")
    story_b = make_story("story-b")
    app = NebulaStoriesApp.__new__(NebulaStoriesApp)
    app.project = StoryProject(selected_story=story_a, shot_plan=[make_shot(1)])
    app.story_by_id = {story_a.id: story_a, story_b.id: story_b}
    app.tree = FakeTree(story_b.id)
    app.details_text = FakeText()
    app.shots_text = FakeText()
    refreshes: list[bool] = []
    app._refresh_render_shots = lambda: refreshes.append(True)

    app._on_select()

    assert app.project.selected_story is story_b
    assert app.project.shot_plan == []
    assert "Create a shot plan" in app.shots_text.value
    assert refreshes == [True]


def test_reselecting_same_story_preserves_loaded_shot_plan() -> None:
    story = make_story("story-a")
    shot_plan = [make_shot(1)]
    app = NebulaStoriesApp.__new__(NebulaStoriesApp)
    app.project = StoryProject(selected_story=story, shot_plan=shot_plan)
    app.story_by_id = {story.id: story}
    app.tree = FakeTree(story.id)
    app.details_text = FakeText()
    app.shots_text = FakeText()
    refreshes: list[bool] = []
    app._refresh_render_shots = lambda: refreshes.append(True)

    app._on_select()

    assert app.project.shot_plan == shot_plan
    assert refreshes == []
