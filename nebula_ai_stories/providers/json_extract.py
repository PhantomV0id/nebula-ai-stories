from __future__ import annotations

import json
import re
from typing import Any

from nebula_ai_stories.models.story import StoryCandidate
from nebula_ai_stories.providers.errors import ProviderOutputError


_FENCED_JSON = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_WRAPPER_KEYS = ("stories", "candidates", "story_candidates")


def _decode_candidate(text: str) -> Any:
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    for match in _FENCED_JSON.finditer(stripped):
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char not in "[{":
            continue
        try:
            value, _end = decoder.raw_decode(stripped[index:])
            return value
        except json.JSONDecodeError:
            continue

    raise ProviderOutputError("Model output did not contain valid JSON")


def extract_story_payloads(text: str, expected_count: int) -> list[dict[str, Any]]:
    if expected_count < 1:
        raise ValueError("expected_count must be at least 1")
    if not isinstance(text, str) or not text.strip():
        raise ProviderOutputError("Model output was empty")

    parsed = _decode_candidate(text)
    if isinstance(parsed, dict):
        for key in _WRAPPER_KEYS:
            wrapped = parsed.get(key)
            if isinstance(wrapped, list):
                parsed = wrapped
                break

    if not isinstance(parsed, list):
        raise ProviderOutputError("Model output JSON must be an array of stories")
    if len(parsed) != expected_count:
        raise ProviderOutputError(f"Model returned {len(parsed)} stories; expected {expected_count}")

    payloads: list[dict[str, Any]] = []
    for index, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            raise ProviderOutputError(f"Model output story {index} is not a JSON object")
        normalized = dict(item)
        normalized["id"] = f"story-{index:03d}"
        try:
            validated = StoryCandidate.from_dict(normalized)
        except (TypeError, ValueError, KeyError) as exc:
            raise ProviderOutputError(f"Model output story {index} is invalid: {exc}") from exc
        payloads.append(validated.to_dict())
    return payloads
