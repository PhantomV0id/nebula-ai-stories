from __future__ import annotations

import json
import mimetypes
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from nebula_ai_stories.comfyui.config import ComfyUIConfig
from nebula_ai_stories.comfyui.errors import (
    ComfyUIConnectionError,
    ComfyUIError,
    ComfyUIResponseError,
    RenderExecutionError,
    RenderTimeoutError,
)
from nebula_ai_stories.comfyui.models import ComfyUIHealth, RenderArtifact, UploadedImage


SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class ComfyUITransport(Protocol):
    def get_json(self, url: str, timeout: float) -> dict[str, Any]: ...

    def post_json(self, url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]: ...

    def post_multipart(
        self,
        url: str,
        fields: dict[str, str],
        file_field: str,
        file_path: Path,
        timeout: float,
    ) -> dict[str, Any]: ...

    def get_bytes(self, url: str, timeout: float) -> bytes: ...


class UrllibComfyUITransport:
    @staticmethod
    def _http_error_detail(exc: HTTPError) -> str:
        try:
            raw = exc.read()
        except OSError:
            return ""
        if not raw:
            return ""
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return raw.decode("utf-8", errors="replace").strip()[:1000]
        if isinstance(parsed, dict):
            parts: list[str] = []
            error = parsed.get("error")
            node_errors = parsed.get("node_errors")
            if error:
                parts.append(str(error))
            if node_errors:
                parts.append(f"node errors: {node_errors}")
            if parts:
                return "; ".join(parts)[:1000]
        return str(parsed)[:1000]

    @staticmethod
    def _request_bytes(request: Request, url: str, timeout: float) -> bytes:
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            detail = UrllibComfyUITransport._http_error_detail(exc)
            suffix = f": {detail}" if detail else ""
            raise ComfyUIResponseError(f"ComfyUI returned HTTP {exc.code} for {url}{suffix}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise ComfyUIConnectionError(f"Could not reach ComfyUI at {url}: {reason}") from exc

    @classmethod
    def _request_json(cls, request: Request, url: str, timeout: float) -> dict[str, Any]:
        raw = cls._request_bytes(request, url, timeout)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ComfyUIResponseError(f"ComfyUI returned malformed JSON from {url}") from exc
        if not isinstance(parsed, dict):
            raise ComfyUIResponseError(f"ComfyUI returned an unexpected response shape from {url}")
        return parsed

    def get_json(self, url: str, timeout: float) -> dict[str, Any]:
        request = Request(url, headers={"Accept": "application/json"}, method="GET")
        return self._request_json(request, url, timeout)

    def post_json(self, url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        return self._request_json(request, url, timeout)

    def post_multipart(
        self,
        url: str,
        fields: dict[str, str],
        file_field: str,
        file_path: Path,
        timeout: float,
    ) -> dict[str, Any]:
        boundary = f"----NebulaStories{uuid.uuid4().hex}"
        body = bytearray()
        for name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            body.extend(value.encode("utf-8"))
            body.extend(b"\r\n")

        filename = file_path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode()
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
        try:
            body.extend(file_path.read_bytes())
        except OSError as exc:
            raise ComfyUIError(f"Could not read keyframe image {file_path}: {exc}") from exc
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())

        request = Request(
            url,
            data=bytes(body),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
            method="POST",
        )
        return self._request_json(request, url, timeout)

    def get_bytes(self, url: str, timeout: float) -> bytes:
        request = Request(url, method="GET")
        return self._request_bytes(request, url, timeout)


class ComfyUIClient:
    def __init__(
        self,
        config: ComfyUIConfig,
        *,
        transport: ComfyUITransport | None = None,
        client_id: str | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.transport = transport or UrllibComfyUITransport()
        self.client_id = client_id or uuid.uuid4().hex
        self.sleep_fn = sleep_fn
        self.monotonic_fn = monotonic_fn

    def health_check(self) -> ComfyUIHealth:
        try:
            info = self.transport.get_json(
                f"{self.config.base_url}/system_stats",
                min(self.config.timeout_seconds, 15.0),
            )
        except ComfyUIError as exc:
            return ComfyUIHealth(False, f"ComfyUI unavailable: {exc}", {})
        return ComfyUIHealth(True, "ComfyUI: Connected", info)

    def upload_image(self, image_path: str | Path) -> UploadedImage:
        path = Path(image_path)
        if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            raise ComfyUIError("Keyframe must be PNG, JPG, JPEG, or WEBP")
        if not path.is_file():
            raise ComfyUIError(f"Keyframe image does not exist: {path}")
        response = self.transport.post_multipart(
            f"{self.config.base_url}/upload/image",
            {"overwrite": "false"},
            "image",
            path,
            self.config.timeout_seconds,
        )
        name = response.get("name")
        subfolder = response.get("subfolder", "")
        image_type = response.get("type", "input")
        if not isinstance(name, str) or not name.strip():
            raise ComfyUIResponseError("ComfyUI upload response is missing image name")
        if not isinstance(subfolder, str) or not isinstance(image_type, str):
            raise ComfyUIResponseError("ComfyUI upload response has invalid subfolder/type")
        return UploadedImage(name.strip(), subfolder.strip(), image_type.strip() or "input")

    def queue_workflow(self, workflow: dict[str, Any]) -> str:
        response = self.transport.post_json(
            f"{self.config.base_url}/prompt",
            {"prompt": workflow, "client_id": self.client_id},
            self.config.timeout_seconds,
        )
        if response.get("error"):
            raise ComfyUIResponseError(f"ComfyUI rejected prompt: {response['error']}")
        prompt_id = response.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            node_errors = response.get("node_errors")
            detail = f"; node errors: {node_errors}" if node_errors else ""
            raise ComfyUIResponseError(f"ComfyUI queue response is missing prompt_id{detail}")
        return prompt_id.strip()

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        return self.transport.get_json(
            f"{self.config.base_url}/history/{prompt_id}",
            self.config.timeout_seconds,
        )

    @staticmethod
    def _execution_error(entry: dict[str, Any]) -> str | None:
        status = entry.get("status")
        if not isinstance(status, dict):
            return None
        messages = status.get("messages", [])
        if isinstance(messages, list):
            for message in messages:
                if not isinstance(message, (list, tuple)) or len(message) < 2:
                    continue
                if str(message[0]).lower() not in {"execution_error", "error"}:
                    continue
                detail = message[1]
                if isinstance(detail, dict):
                    text = detail.get("exception_message") or detail.get("message")
                    if isinstance(text, str) and text.strip():
                        return text.strip()
                return str(detail)
        status_str = status.get("status_str")
        if isinstance(status_str, str) and status_str.lower() in {"error", "failed"}:
            return f"ComfyUI execution status: {status_str}"
        return None

    def wait_for_completion(self, prompt_id: str) -> dict[str, Any]:
        started = self.monotonic_fn()
        while True:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                entry = history[prompt_id]
                if not isinstance(entry, dict):
                    raise ComfyUIResponseError(f"ComfyUI history for {prompt_id} has invalid shape")
                status = entry.get("status")
                if not isinstance(status, dict):
                    raise ComfyUIResponseError(f"ComfyUI history for {prompt_id} has invalid status")
                execution_error = self._execution_error(entry)
                if execution_error:
                    raise RenderExecutionError(f"ComfyUI render failed: {execution_error}")
                outputs = entry.get("outputs")
                completed = status.get("completed") is True
                success = str(status.get("status_str", "")).lower() == "success"
                if completed or success or (isinstance(outputs, dict) and bool(outputs)):
                    if not isinstance(outputs, dict):
                        raise ComfyUIResponseError(f"Completed ComfyUI history for {prompt_id} is missing outputs")
                    return entry

            if self.monotonic_fn() - started >= self.config.timeout_seconds:
                raise RenderTimeoutError(
                    f"ComfyUI prompt {prompt_id} did not complete within {self.config.timeout_seconds:g} seconds"
                )
            self.sleep_fn(self.config.poll_interval_seconds)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        base = Path(filename.replace("\\", "/")).name
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip(".-")
        return safe or "artifact.bin"

    def download_artifact(self, artifact: RenderArtifact, destination: str | Path) -> RenderArtifact:
        query = urlencode(
            {
                "filename": artifact.filename,
                "subfolder": artifact.subfolder,
                "type": artifact.type,
            }
        )
        data = self.transport.get_bytes(
            f"{self.config.base_url}/view?{query}",
            self.config.timeout_seconds,
        )
        output_dir = Path(destination)
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._safe_filename(artifact.filename)
        target = output_dir / filename
        counter = 2
        while target.exists():
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            target = output_dir / f"{stem}-{counter}{suffix}"
            counter += 1
        try:
            target.write_bytes(data)
        except OSError as exc:
            raise ComfyUIError(f"Could not save ComfyUI artifact to {target}: {exc}") from exc
        return replace(artifact, local_path=target)
