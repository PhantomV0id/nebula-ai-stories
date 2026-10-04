from __future__ import annotations

from nebula_ai_stories.models.story import StoryCandidate, StoryScore
from nebula_ai_stories.story.novelty import NoveltyEngine


class StoryScorer:
    """Transparent V1 heuristics. These scores are not an LLM judgment."""

    def score(self, story: StoryCandidate, *, novelty: float = 10.0) -> StoryScore:
        hook_strength = 5.0 + min(3.0, len(story.hook.split()) / 8.0)
        if any(word in story.hook.lower() for word in ("stuck", "falls", "strains", "backs", "vibrates", "rolls")):
            hook_strength += 1.0

        visual_clarity = 9.0
        visual_clarity -= max(0, len(story.visual_requirements) - 4) * 0.7
        visual_clarity -= min(2.0, len(story.dialogue_lines) * 0.8)

        conflict_strength = 5.5 + min(3.5, len(story.problem.split()) / 7.0)
        payoff_strength = 5.0 + min(3.0, len(story.payoff.split()) / 8.0)
        if story.twist.strip() and story.twist.strip().lower() != story.payoff.strip().lower():
            payoff_strength += 0.8

        emotional_strength = 5.5
        emotion_text = f"{story.emotion} {' '.join(story.tags)}".lower()
        if any(word in emotion_text for word in ("comedy", "wholesome", "cute")):
            emotional_strength += 2.0
        if "role-reversal" in story.tags or "fear-inversion" in story.tags:
            emotional_strength += 0.7

        feasibility_by_difficulty = {"easy": 9.2, "moderate": 7.3, "hard": 5.2}
        generation_feasibility = feasibility_by_difficulty[story.generation_difficulty]
        generation_feasibility -= max(0, len(story.visual_requirements) - 4) * 0.4
        generation_feasibility -= max(0, len(story.dialogue_lines) - 1) * 0.5

        components = {
            "hook_strength": hook_strength,
            "visual_clarity": visual_clarity,
            "conflict_strength": conflict_strength,
            "payoff_strength": payoff_strength,
            "emotional_strength": emotional_strength,
            "generation_feasibility": generation_feasibility,
            "novelty": novelty,
        }
        weights = {
            "hook_strength": 0.18,
            "visual_clarity": 0.16,
            "conflict_strength": 0.12,
            "payoff_strength": 0.18,
            "emotional_strength": 0.12,
            "generation_feasibility": 0.14,
            "novelty": 0.10,
        }
        overall = sum(max(0.0, min(10.0, components[name])) * weight for name, weight in weights.items())
        rejected = story.generation_difficulty == "hard" and generation_feasibility < 4.0
        return StoryScore(
            **components,
            overall_score=overall,
            rejected=rejected,
            rejection_reason="Generation feasibility is too low for V1." if rejected else None,
        )


def rank_candidates(
    candidates: list[StoryCandidate],
    scorer: StoryScorer | None = None,
    novelty_engine: NoveltyEngine | None = None,
) -> list[tuple[StoryCandidate, StoryScore]]:
    scorer = scorer or StoryScorer()
    novelty_engine = novelty_engine or NoveltyEngine()
    scored: list[tuple[StoryCandidate, StoryScore]] = []
    seen: list[StoryCandidate] = []
    for candidate in candidates:
        novelty = novelty_engine.novelty_score(candidate, seen)
        scored.append((candidate, scorer.score(candidate, novelty=novelty)))
        seen.append(candidate)
    return sorted(scored, key=lambda item: item[1].overall_score, reverse=True)

