from __future__ import annotations

from nebula_ai_stories.models.shot import Shot
from nebula_ai_stories.models.story import StoryCandidate
from nebula_ai_stories.story.prompts import build_image_prompt, build_motion_prompt


class ShotPlanner:
    def plan(self, story: StoryCandidate) -> list[Shot]:
        total = max(8.0, min(15.0, story.estimated_duration_seconds))
        first = round(total * 0.30, 1)
        second = round(total * 0.36, 1)
        third = round(total - first - second, 1)

        camera = "eye-level phone camera, mostly static with subtle handheld drift"
        characters = [value for value in story.visual_requirements if self._looks_like_character(value)]
        props = [value for value in story.visual_requirements if value not in characters]

        shots = [
            Shot(
                shot_index=1,
                duration_seconds=first,
                story_function="Hook / problem",
                visual_description=f"{story.hook} {story.problem}",
                image_prompt=build_image_prompt(f"{story.hook} {story.problem}", camera),
                motion_prompt=build_motion_prompt(story.hook),
                camera=camera,
                characters=characters,
                props=props,
                continuity_notes="Establish all important characters, props, and spatial relationships immediately.",
            ),
            Shot(
                shot_index=2,
                duration_seconds=second,
                story_function="Action / twist",
                visual_description=f"{story.action} {story.twist}",
                image_prompt=build_image_prompt(f"{story.action} {story.twist}", camera),
                motion_prompt=build_motion_prompt(f"{story.action} Then {story.twist}"),
                camera=camera,
                characters=characters,
                props=props,
                continuity_notes="Keep wardrobe, character appearance, prop placement, and environment consistent with shot 1.",
            ),
            Shot(
                shot_index=3,
                duration_seconds=third,
                story_function="Payoff",
                visual_description=story.payoff,
                image_prompt=build_image_prompt(story.payoff, camera),
                motion_prompt=build_motion_prompt(story.payoff),
                camera=camera,
                characters=characters,
                props=props,
                continuity_notes="Complete the payoff clearly in frame and hold the readable reaction briefly at the end.",
            ),
        ]
        return shots

    @staticmethod
    def _looks_like_character(value: str) -> bool:
        terms = ("adult", "baby", "bird", "cat", "child", "crow", "dog", "duck", "kitten", "parrot", "pigeon", "puppy", "rabbit", "squirrel", "toddler", "tortoise")
        lowered = value.lower()
        return any(term in lowered for term in terms)

