from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError

import pytest

from nebula_ai_stories.providers.config import ProviderConfig
from nebula_ai_stories.providers.errors import (
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderOutputError,
)
from nebula_ai_stories.providers.factory import create_provider
from nebula_ai_stories.providers.http import post_json
from nebula_ai_stories.providers.json_extract import extract_story_payloads
from nebula_ai_stories.providers.lm_studio import LMStudioProvider
from nebula_ai_stories.providers.mock_provider import MockProvider
from nebula_ai_stories.providers.ollama import OllamaProvider
from nebula_ai_stories.story.generation_prompt import build_story_generation_prompt


def story_payload(index: int = 1) -> dict[str, Any]:
    return {
        "id": f"story-{index:03d}",
        "title": f"Story {index}",
        "premise": "A dog and cat solve a small visible household problem together.",
        "hook": "A toy rolls toward the edge of a low table.",
        "problem": "Neither animal can stop it from their current position.",
        "action": "The dog nudges a cushion into the toy's path.",
        "twist": "The cat jumps onto the cushion and blocks the toy first.",
        "payoff": "The toy stops safely and both animals stare at each other.",
        "emotion": "comedy",
        "estimated_duration_seconds": 11,
        "dialogue_lines": [],
        "visual_requirements": ["dog", "cat", "toy", "low table"],
        "generation_difficulty": "easy",
        "story_mechanics": ["rolling object risk", "improvised block", "unexpected cooperation"],
        "tags": ["comedy", "cooperation"],
    }


def test_provider_config_applies_local_defaults_without_hard_coding_model() -> None:
    lm = ProviderConfig(provider_type="lm_studio")
    ollama = ProviderConfig(provider_type="ollama")

    assert lm.base_url == "http://127.0.0.1:1234"
    assert ollama.base_url == "http://127.0.0.1:11434"
    assert lm.model == ""
    assert ollama.model == ""
    assert lm.timeout_seconds > 0
    assert 0 <= lm.temperature <= 2


def test_provider_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="provider_type"):
        ProviderConfig(provider_type="cloud")
    with pytest.raises(ValueError, match="timeout_seconds"):
        ProviderConfig(timeout_seconds=0)
    with pytest.raises(ValueError, match="temperature"):
        ProviderConfig(temperature=3)


def test_json_extraction_accepts_plain_fenced_and_wrapped_json() -> None:
    stories = [story_payload(1), story_payload(2)]
    plain = json.dumps(stories)
    fenced = f"```json\n{plain}\n```"
    wrapped = json.dumps({"stories": stories})

    assert extract_story_payloads(plain, 2) == stories
    assert extract_story_payloads(fenced, 2) == stories
    assert extract_story_payloads(wrapped, 2) == stories


def test_json_extraction_can_recover_json_after_small_model_preamble() -> None:
    stories = [story_payload(1)]
    text = "Here is the JSON you requested:\n" + json.dumps(stories)

    assert extract_story_payloads(text, 1) == stories


def test_json_extraction_rejects_wrong_count_and_invalid_story_shape() -> None:
    with pytest.raises(ProviderOutputError, match="expected 2"):
        extract_story_payloads(json.dumps([story_payload(1)]), 2)

    broken = story_payload(1)
    del broken["payoff"]
    with pytest.raises(ProviderOutputError, match="story 1"):
        extract_story_payloads(json.dumps([broken]), 1)


def test_generation_prompt_demands_exact_count_json_and_distinct_mechanics() -> None:
    prompt = build_story_generation_prompt(20)

    assert "exactly 20" in prompt.lower()
    assert "json" in prompt.lower()
    assert "story_mechanics" in prompt
    assert "object-swap" in prompt.lower()
    assert "8–15" in prompt or "8-15" in prompt


def test_lm_studio_provider_sends_openai_compatible_non_streaming_request() -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
        captured.update(url=url, body=body, timeout=timeout)
        return {"choices": [{"message": {"content": json.dumps([story_payload(1), story_payload(2)])}}]}

    config = ProviderConfig(
        provider_type="lm_studio",
        model="local-model",
        timeout_seconds=42,
        temperature=0.55,
        max_tokens=3000,
    )
    provider = LMStudioProvider(config, request_fn=fake_post)

    result = provider.generate_story_payloads(2)

    assert len(result) == 2
    assert captured["url"] == "http://127.0.0.1:1234/v1/chat/completions"
    assert captured["timeout"] == 42
    assert captured["body"]["model"] == "local-model"
    assert captured["body"]["temperature"] == 0.55
    assert captured["body"]["stream"] is False
    assert captured["body"]["max_tokens"] == 3000
    assert [message["role"] for message in captured["body"]["messages"]] == ["system", "user"]


def test_ollama_provider_sends_non_streaming_chat_request() -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
        captured.update(url=url, body=body, timeout=timeout)
        return {"message": {"role": "assistant", "content": json.dumps([story_payload(1)])}}

    config = ProviderConfig(
        provider_type="ollama",
        model="qwen-local",
        timeout_seconds=90,
        temperature=0.7,
        max_tokens=2048,
    )
    provider = OllamaProvider(config, request_fn=fake_post)

    result = provider.generate_story_payloads(1)

    assert len(result) == 1
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["timeout"] == 90
    assert captured["body"]["model"] == "qwen-local"
    assert captured["body"]["stream"] is False
    assert captured["body"]["format"] == "json"
    assert captured["body"]["options"]["temperature"] == 0.7
    assert captured["body"]["options"]["num_predict"] == 2048


def test_real_local_provider_requires_model_name() -> None:
    with pytest.raises(ProviderConfigurationError, match="model"):
        LMStudioProvider(ProviderConfig(provider_type="lm_studio"))
    with pytest.raises(ProviderConfigurationError, match="model"):
        OllamaProvider(ProviderConfig(provider_type="ollama"))


def test_provider_factory_returns_requested_provider() -> None:
    assert isinstance(create_provider(ProviderConfig(provider_type="mock")), MockProvider)
    assert isinstance(
        create_provider(ProviderConfig(provider_type="lm_studio", model="model-a")),
        LMStudioProvider,
    )
    assert isinstance(
        create_provider(ProviderConfig(provider_type="ollama", model="model-b")),
        OllamaProvider,
    )


def test_http_transport_turns_url_error_into_user_facing_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_urlopen(*_args: Any, **_kwargs: Any) -> Any:
        raise URLError("connection refused")

    monkeypatch.setattr("nebula_ai_stories.providers.http.urlopen", failing_urlopen)

    with pytest.raises(ProviderConnectionError, match="Could not reach local AI server"):
        post_json("http://127.0.0.1:1234/test", {"hello": "world"}, 5)


def test_provider_reports_malformed_server_response_clearly() -> None:
    def bad_lm_response(_url: str, _body: dict[str, Any], _timeout: float) -> dict[str, Any]:
        return {"choices": []}

    provider = LMStudioProvider(
        ProviderConfig(provider_type="lm_studio", model="local-model"),
        request_fn=bad_lm_response,
    )

    with pytest.raises(ProviderOutputError, match="LM Studio"):
        provider.generate_story_payloads(1)
