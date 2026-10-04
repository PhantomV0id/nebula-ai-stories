from __future__ import annotations


SYSTEM_PROMPT = """You are the story ideation engine for Nebula AI Stories.
Return JSON only. Do not add markdown, code fences, commentary, explanations, or prose outside the JSON.
Your stories will become short vertical AI-generated candid phone videos, so prefer simple visible actions and believable environments."""


def build_story_generation_prompt(count: int) -> str:
    if count < 1:
        raise ValueError("count must be at least 1")
    return f"""Generate exactly {count} original StoryCandidate objects as one JSON array.

Every object MUST contain these keys:
id, title, premise, hook, problem, action, twist, payoff, emotion,
estimated_duration_seconds, dialogue_lines, visual_requirements,
generation_difficulty, story_mechanics, tags.

Rules:
- estimated_duration_seconds must be 8–15 seconds.
- The first second must already show the situation or problem clearly.
- Use one visually obvious situation, one simple conflict, simple physical actions, and one clear visual payoff.
- Use only 1–3 important characters. Keep dialogue empty or extremely short. The story must work without sound.
- Make the concept internationally understandable and avoid jokes that depend on written text.
- Favor comedy, wholesome/helping, role reversal, fear inversion, misunderstanding, problem-solution, or unexpected cooperation.
- Keep environments ordinary and believable. Keep choreography limited and generation difficulty realistic.
- Avoid epic/cinematic storytelling, exposition, long dialogue, complicated plots, multiple scene changes, graphic harm, and dangerous actions involving children.
- Avoid generic inspirational stories.
- Every item in this batch must use genuinely different STORY MECHANICS.
- Do not make object-swap duplicates such as the same "child drops object → dog returns it" mechanic with a ball, spoon, sock, or other prop.
- story_mechanics must describe the causal mechanic, not merely list props.
- generation_difficulty must be exactly one of: easy, moderate, hard.
- id values must be unique strings such as story-001, story-002, ...

Output JSON array only."""
