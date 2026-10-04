from __future__ import annotations

from pathlib import Path

import pytest

from nebula_ai_stories.models.project import StoryProject
from nebula_ai_stories.providers.mock_provider import MockProvider
from nebula_ai_stories.storage.project_store import ProjectLoadError, ProjectStore
from nebula_ai_stories.story.generator import StoryGenerator
from nebula_ai_stories.story.novelty import NoveltyEngine
from nebula_ai_stories.story.planner import ShotPlanner
from nebula_ai_stories.story.scorer import StoryScorer, rank_candidates


def populated_project() -> StoryProject:
    candidates = StoryGenerator(MockProvider()).generate_candidates(4)
    ranked = rank_candidates(candidates, StoryScorer(), NoveltyEngine())
    scores = {candidate.id: score for candidate, score in ranked}
    selected = ranked[0][0]
    shots = ShotPlanner().plan(selected)
    return StoryProject(
        generated_candidates=candidates,
        scores=scores,
        selected_story=selected,
        shot_plan=shots,
    )


def test_project_save_load_roundtrip_preserves_important_data(tmp_path: Path) -> None:
    store = ProjectStore()
    path = tmp_path / "story-project.json"
    original = populated_project()

    store.save(original, path)
    loaded = store.load(path)

    assert loaded.schema_version == original.schema_version
    assert [story.id for story in loaded.generated_candidates] == [story.id for story in original.generated_candidates]
    assert loaded.selected_story is not None
    assert loaded.selected_story.id == original.selected_story.id
    assert loaded.scores.keys() == original.scores.keys()
    assert len(loaded.shot_plan) == len(original.shot_plan)
    assert loaded.updated_at >= original.updated_at


def test_malformed_project_json_fails_gracefully(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{ definitely not json", encoding="utf-8")

    with pytest.raises(ProjectLoadError, match="malformed"):
        ProjectStore().load(path)


def test_missing_required_project_data_fails_gracefully(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"
    path.write_text('{"schema_version": 1}', encoding="utf-8")

    with pytest.raises(ProjectLoadError, match="missing"):
        ProjectStore().load(path)


def test_unsupported_schema_fails_gracefully(tmp_path: Path) -> None:
    path = tmp_path / "future.json"
    path.write_text(
        '{"schema_version": 999, "created_at": "2026-01-01T00:00:00+00:00", '
        '"updated_at": "2026-01-01T00:00:00+00:00", "generated_candidates": [], '
        '"scores": {}, "selected_story": null, "shot_plan": []}',
        encoding="utf-8",
    )

    with pytest.raises(ProjectLoadError, match="unsupported"):
        ProjectStore().load(path)
