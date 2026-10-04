from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from nebula_ai_stories.providers.errors import ProviderConnectionError, ProviderResponseError


def _read_json_response(request: Request, url: str, timeout: float) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ProviderResponseError(f"Local AI server returned HTTP {exc.code} for {url}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise ProviderConnectionError(f"Could not reach local AI server at {url}: {reason}") from exc

    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderResponseError(f"Local AI server returned malformed JSON from {url}") from exc
    if not isinstance(parsed, dict):
        raise ProviderResponseError(f"Local AI server returned an unexpected response shape from {url}")
    return parsed


def get_json(url: str, timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    return _read_json_response(request, url, timeout)


def post_json(url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    return _read_json_response(request, url, timeout)
