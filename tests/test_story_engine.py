from __future__ import annotations

import pytest

from nebula_ai_stories.models.story import StoryCandidate, StoryScore
from nebula_ai_stories.providers.mock_provider import MockProvider
from nebula_ai_stories.story.generator import StoryGenerator
from nebula_ai_stories.story.novelty import NoveltyEngine
from nebula_ai_stories.story.planner import ShotPlanner
from nebula_ai_stories.story.scorer import StoryScorer, rank_candidates


def make_story(**overrides: object) -> StoryCandidate:
    values: dict[str, object] = {
        "id": "story-1",
        "title": "Dog Opens the Door",
        "premise": "A child is stuck outside until the family dog nudges the door open.",
        "hook": "A child presses both hands against a closed glass door.",
        "problem": "The handle is too high to reach.",
        "action": "The child points at the handle while the dog watches.",
        "twist": "The dog jumps up and bumps the lever handle.",
        "payoff": "The door opens and the child hugs the dog.",
        "emotion": "wholesome",
        "estimated_duration_seconds": 11.0,
        "dialogue_lines": [],
        "visual_requirements": ["child", "dog", "glass door"],
        "generation_difficulty": "easy",
        "story_mechanics": ["cannot reach object", "dog helps", "problem solved"],
        "tags": ["wholesome", "helping", "dog"],
    }
    values.update(overrides)
    return StoryCandidate(**values)


def test_story_candidate_validation_rejects_out_of_range_duration() -> None:
    with pytest.raises(ValueError, match="8 and 15"):
        make_story(estimated_duration_seconds=20.0)


def test_story_candidate_requires_core_story_text() -> None:
    with pytest.raises(ValueError, match="title"):
        make_story(title="")


def test_story_score_clamps_values_to_zero_through_ten() -> None:
    score = StoryScore(
        hook_strength=14,
        visual_clarity=-3,
        conflict_strength=8,
        payoff_strength=11,
        emotional_strength=7,
        generation_feasibility=6,
        novelty=15,
        overall_score=-2,
    )

    assert score.hook_strength == 10
    assert score.visual_clarity == 0
    assert score.payoff_strength == 10
    assert score.novelty == 10
    assert score.overall_score == 0


@pytest.mark.parametrize("count", [1, 7, 20, 25])
def test_generate_candidates_returns_exact_requested_count(count: int) -> None:
    generator = StoryGenerator(MockProvider())

    candidates = generator.generate_candidates(count=count)

    assert len(candidates) == count
    assert len({candidate.id for candidate in candidates}) == count
    assert all(8 <= candidate.estimated_duration_seconds <= 15 for candidate in candidates)


def test_mock_generation_covers_multiple_story_families() -> None:
    candidates = StoryGenerator(MockProvider()).generate_candidates(count=20)
    families = {tag for candidate in candidates for tag in candidate.tags}

    assert {"comedy", "wholesome", "role-reversal", "fear-inversion", "misunderstanding"} <= families


def test_ranking_returns_highest_overall_score_first() -> None:
    stories = [
        make_story(id="a", title="A", payoff="Tiny payoff", story_mechanics=["simple action"]),
        make_story(
            id="b",
            title="B",
            hook="A puppy is visibly trapped behind a baby gate in the first instant.",
            problem="The puppy cannot cross the gate.",
            action="A toddler studies the latch and reaches for it.",
            twist="The toddler opens it, then the puppy closes it behind the toddler.",
            payoff="They stare at each other, then both waggle excitedly at the gate.",
            emotion="comedy wholesome",
            story_mechanics=["blocked path", "human helps animal", "role reversal"],
            tags=["comedy", "wholesome", "role-reversal"],
        ),
    ]

    ranked = rank_candidates(stories, StoryScorer(), NoveltyEngine())

    assert ranked[0][1].overall_score >= ranked[1][1].overall_score
    assert {item[0].id for item in ranked} == {"a", "b"}


def test_near_duplicate_story_mechanics_are_detected() -> None:
    engine = NoveltyEngine()
    cookie = make_story(
        id="cookie",
        story_mechanics=["child cannot reach object", "dog helps child", "object retrieved"],
        tags=["wholesome", "dog", "helping"],
    )
    toy = make_story(
        id="toy",
        story_mechanics=["child cannot reach object", "dog helps child", "object retrieved"],
        tags=["wholesome", "dog", "helping"],
    )

    assert engine.are_duplicates(cookie, toy)
    assert engine.similarity(cookie, toy) >= engine.duplicate_threshold


def test_meaningfully_different_story_mechanics_are_not_duplicates() -> None:
    engine = NoveltyEngine()
    helping = make_story(id="help", story_mechanics=["blocked access", "dog helps child", "problem solved"])
    misunderstanding = make_story(
        id="mixup",
        story_mechanics=["mistaken ownership", "cat hides evidence", "visual reveal"],
        tags=["comedy", "misunderstanding", "cat"],
    )

    assert not engine.are_duplicates(helping, misunderstanding)


def test_shot_planner_generates_two_to_four_shots_in_target_duration() -> None:
    shots = ShotPlanner().plan(make_story(estimated_duration_seconds=12.0))

    assert 2 <= len(shots) <= 4
    assert 8 <= sum(shot.duration_seconds for shot in shots) <= 15


def test_shot_planner_first_shot_establishes_hook_and_final_shot_completes_payoff() -> None:
    story = make_story()
    shots = ShotPlanner().plan(story)

    assert "hook" in shots[0].story_function.lower() or "problem" in shots[0].story_function.lower()
    assert "payoff" in shots[-1].story_function.lower()
    assert story.payoff.lower() in shots[-1].visual_description.lower()


def test_shot_prompts_keep_image_and_motion_concerns_separate() -> None:
    shot = ShotPlanner().plan(make_story())[0]

    assert "smartphone" in shot.image_prompt.lower()
    assert "movement" in shot.motion_prompt.lower() or "motion" in shot.motion_prompt.lower()
    assert shot.image_prompt != shot.motion_prompt
