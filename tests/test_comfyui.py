from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

from nebula_ai_stories.comfyui.artifacts import discover_artifacts
from nebula_ai_stories.comfyui.bindings import load_binding_profile, patch_workflow
from nebula_ai_stories.comfyui.client import ComfyUIClient, UrllibComfyUITransport
from nebula_ai_stories.comfyui.config import ComfyUIConfig
from nebula_ai_stories.comfyui.errors import (
    ComfyUIConnectionError,
    ComfyUIResponseError,
    RenderExecutionError,
    RenderTimeoutError,
    WorkflowBindingError,
    WorkflowFormatError,
)
from nebula_ai_stories.comfyui.models import BindingProfile, RenderArtifact, UploadedImage, WorkflowBinding
from nebula_ai_stories.comfyui.service import ComfyRenderService
from nebula_ai_stories.comfyui.workflow import load_api_workflow, validate_api_workflow
from nebula_ai_stories.models.shot import Shot
from nebula_ai_stories.storage.comfyui_settings_store import ComfyUISettingsStore


def api_workflow() -> dict[str, Any]:
    return {
        "101": {"class_type": "CLIPTextEncode", "inputs": {"text": "old image"}},
        "102": {"class_type": "CLIPTextEncode", "inputs": {"text": "old motion"}},
        "45": {"class_type": "LoadImage", "inputs": {"image": "old.png"}},
        "74": {"class_type": "KSampler", "inputs": {"seed": 1}},
        "90": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "old"}},
    }


def binding_profile() -> BindingProfile:
    return BindingProfile(
        name="test-profile",
        bindings={
            "image_prompt": WorkflowBinding("101", "text"),
            "motion_prompt": WorkflowBinding("102", "text"),
            "input_image": WorkflowBinding("45", "image"),
            "seed": WorkflowBinding("74", "seed"),
            "output_prefix": WorkflowBinding("90", "filename_prefix"),
        },
    )


def make_shot() -> Shot:
    return Shot(
        shot_index=1,
        duration_seconds=4.0,
        story_function="Hook / problem",
        visual_description="A dog watches a toy roll toward the edge of a table.",
        image_prompt="realistic phone frame of dog and rolling toy",
        motion_prompt="toy rolls slowly; dog nudges a cushion",
        camera="handheld medium shot",
        characters=["dog"],
        props=["toy", "cushion"],
    )


class FakeTransport:
    def __init__(self) -> None:
        self.get_responses: list[Any] = []
        self.post_responses: list[Any] = []
        self.multipart_response: Any = {"name": "frame.png", "subfolder": "", "type": "input"}
        self.bytes_response = b"artifact-bytes"
        self.calls: list[tuple[Any, ...]] = []

    @staticmethod
    def _next(items: list[Any]) -> Any:
        if not items:
            raise AssertionError("fake response queue is empty")
        value = items.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def get_json(self, url: str, timeout: float) -> dict[str, Any]:
        self.calls.append(("get_json", url, timeout))
        return self._next(self.get_responses)

    def post_json(self, url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
        self.calls.append(("post_json", url, body, timeout))
        return self._next(self.post_responses)

    def post_multipart(
        self,
        url: str,
        fields: dict[str, str],
        file_field: str,
        file_path: Path,
        timeout: float,
    ) -> dict[str, Any]:
        self.calls.append(("post_multipart", url, fields, file_field, file_path, timeout))
        if isinstance(self.multipart_response, Exception):
            raise self.multipart_response
        return self.multipart_response

    def get_bytes(self, url: str, timeout: float) -> bytes:
        self.calls.append(("get_bytes", url, timeout))
        if isinstance(self.bytes_response, Exception):
            raise self.bytes_response
        return self.bytes_response


def test_comfyui_config_defaults() -> None:
    config = ComfyUIConfig()

    assert config.base_url == "http://127.0.0.1:8188"
    assert config.timeout_seconds > 0
    assert config.poll_interval_seconds > 0
    assert config.workflow_path is None
    assert config.binding_profile_path is None


def test_comfyui_settings_save_load_roundtrip(tmp_path: Path) -> None:
    settings_path = tmp_path / "comfyui-settings.json"
    config = ComfyUIConfig(
        base_url="http://127.0.0.1:8189/",
        timeout_seconds=321,
        poll_interval_seconds=1.5,
        workflow_path=tmp_path / "workflow.json",
        binding_profile_path=tmp_path / "profile.json",
    )

    store = ComfyUISettingsStore(settings_path)
    store.save(config)

    assert store.load() == config


def test_comfyui_settings_invalid_base_url_type_falls_back_to_defaults(tmp_path: Path) -> None:
    settings_path = tmp_path / "comfyui-settings.json"
    settings_path.write_text(json.dumps({"base_url": 123}), encoding="utf-8")

    config = ComfyUISettingsStore(settings_path).load()

    assert config == ComfyUIConfig()


def test_health_check_success() -> None:
    transport = FakeTransport()
    transport.get_responses = [{"system": {"os": "nt"}, "devices": [{"name": "RTX 3090"}]}]
    client = ComfyUIClient(ComfyUIConfig(), transport=transport)

    health = client.health_check()

    assert health.available is True
    assert health.message == "ComfyUI: Connected"
    assert health.system_info["system"]["os"] == "nt"
    assert transport.calls[0][1] == "http://127.0.0.1:8188/system_stats"


def test_health_check_connection_failure_returns_clean_status() -> None:
    transport = FakeTransport()
    transport.get_responses = [ComfyUIConnectionError("connection refused")]
    client = ComfyUIClient(ComfyUIConfig(), transport=transport)

    health = client.health_check()

    assert health.available is False
    assert "ComfyUI unavailable" in health.message
    assert "connection refused" in health.message


def test_api_workflow_validation_accepts_prompt_json(tmp_path: Path) -> None:
    path = tmp_path / "workflow-api.json"
    path.write_text(json.dumps(api_workflow()), encoding="utf-8")

    loaded = load_api_workflow(path)

    assert loaded["101"]["class_type"] == "CLIPTextEncode"


def test_ui_workflow_json_is_rejected_with_useful_message() -> None:
    ui_workflow = {"last_node_id": 2, "nodes": [{"id": 1, "type": "LoadImage"}], "links": []}

    with pytest.raises(WorkflowFormatError, match="API format"):
        validate_api_workflow(ui_workflow)


def test_binding_profile_parsing(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps(
            {
                "name": "wan-example",
                "bindings": {
                    "image_prompt": {"node_id": "101", "input_name": "text"},
                    "input_image": {"node_id": "45", "input_name": "image"},
                },
            }
        ),
        encoding="utf-8",
    )

    profile = load_binding_profile(path)

    assert profile.name == "wan-example"
    assert profile.bindings["image_prompt"] == WorkflowBinding("101", "text")


def test_image_prompt_binding_patches_only_configured_node_and_input() -> None:
    workflow = api_workflow()
    original_motion = workflow["102"]["inputs"]["text"]

    patched = patch_workflow(workflow, binding_profile(), {"image_prompt": "new image prompt"})

    assert patched["101"]["inputs"]["text"] == "new image prompt"
    assert patched["102"]["inputs"]["text"] == original_motion


def test_motion_prompt_binding_works_independently() -> None:
    patched = patch_workflow(api_workflow(), binding_profile(), {"motion_prompt": "new motion prompt"})

    assert patched["102"]["inputs"]["text"] == "new motion prompt"
    assert patched["101"]["inputs"]["text"] == "old image"


def test_input_image_binding_works() -> None:
    patched = patch_workflow(api_workflow(), binding_profile(), {"input_image": "nebula/frame.png"})

    assert patched["45"]["inputs"]["image"] == "nebula/frame.png"


def test_missing_binding_node_raises_workflow_binding_error() -> None:
    profile = BindingProfile("bad", {"image_prompt": WorkflowBinding("999", "text")})

    with pytest.raises(WorkflowBindingError, match="node 999"):
        patch_workflow(api_workflow(), profile, {"image_prompt": "prompt"})


def test_missing_binding_input_raises_workflow_binding_error() -> None:
    profile = BindingProfile("bad", {"image_prompt": WorkflowBinding("101", "missing_input")})

    with pytest.raises(WorkflowBindingError, match="missing_input"):
        patch_workflow(api_workflow(), profile, {"image_prompt": "prompt"})


def test_workflow_patching_does_not_mutate_original() -> None:
    workflow = api_workflow()

    patched = patch_workflow(workflow, binding_profile(), {"seed": 99})

    assert patched["74"]["inputs"]["seed"] == 99
    assert workflow["74"]["inputs"]["seed"] == 1


def test_image_upload_request_parsing(tmp_path: Path) -> None:
    image = tmp_path / "frame.png"
    image.write_bytes(b"png")
    transport = FakeTransport()
    transport.multipart_response = {"name": "frame.png", "subfolder": "nebula", "type": "input"}
    client = ComfyUIClient(ComfyUIConfig(), transport=transport)

    uploaded = client.upload_image(image)

    assert uploaded == UploadedImage("frame.png", "nebula", "input")
    assert uploaded.comfyui_path == "nebula/frame.png"
    assert transport.calls[0][0] == "post_multipart"
    assert transport.calls[0][1] == "http://127.0.0.1:8188/upload/image"


def test_queue_request_returns_prompt_id() -> None:
    transport = FakeTransport()
    transport.post_responses = [{"prompt_id": "prompt-123", "number": 1, "node_errors": {}}]
    client = ComfyUIClient(ComfyUIConfig(), transport=transport, client_id="client-1")

    prompt_id = client.queue_workflow(api_workflow())

    assert prompt_id == "prompt-123"
    _, _, body, _ = transport.calls[0]
    assert body["client_id"] == "client-1"
    assert body["prompt"] == api_workflow()


def test_malformed_queue_response_fails_clearly() -> None:
    transport = FakeTransport()
    transport.post_responses = [{"node_errors": {}}]
    client = ComfyUIClient(ComfyUIConfig(), transport=transport)

    with pytest.raises(ComfyUIResponseError, match="prompt_id"):
        client.queue_workflow(api_workflow())


def test_rejected_prompt_fails_clearly() -> None:
    transport = FakeTransport()
    transport.post_responses = [{"error": "prompt validation failed", "node_errors": {"45": "bad image"}}]
    client = ComfyUIClient(ComfyUIConfig(), transport=transport)

    with pytest.raises(ComfyUIResponseError, match="rejected prompt.*validation failed"):
        client.queue_workflow(api_workflow())


def test_http_prompt_rejection_preserves_json_error_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "http://127.0.0.1:8188/prompt"
    payload = json.dumps(
        {"error": "prompt validation failed", "node_errors": {"45": {"errors": ["bad image"]}}}
    ).encode("utf-8")
    error = HTTPError(url, 400, "Bad Request", hdrs=None, fp=BytesIO(payload))

    def reject_prompt(*_args: Any, **_kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr("nebula_ai_stories.comfyui.client.urlopen", reject_prompt)
    transport = UrllibComfyUITransport()

    with pytest.raises(ComfyUIResponseError, match="HTTP 400.*prompt validation failed.*node errors"):
        transport.post_json(url, {"prompt": api_workflow()}, 1)


def test_history_polling_detects_completion() -> None:
    transport = FakeTransport()
    transport.get_responses = [
        {},
        {
            "p1": {
                "status": {"completed": True, "status_str": "success", "messages": []},
                "outputs": {"90": {"videos": [{"filename": "out.mp4", "subfolder": "", "type": "output"}]}},
            }
        },
    ]
    now = iter([0.0, 0.1, 0.2, 0.3])
    client = ComfyUIClient(
        ComfyUIConfig(timeout_seconds=10, poll_interval_seconds=0.01),
        transport=transport,
        sleep_fn=lambda _seconds: None,
        monotonic_fn=lambda: next(now),
    )

    history = client.wait_for_completion("p1")

    assert history["status"]["completed"] is True
    assert len([call for call in transport.calls if call[0] == "get_json"]) == 2


def test_malformed_history_entry_fails_clearly() -> None:
    transport = FakeTransport()
    transport.get_responses = [{"p1": ["unexpected"]}]
    client = ComfyUIClient(ComfyUIConfig(), transport=transport, sleep_fn=lambda _seconds: None)

    with pytest.raises(ComfyUIResponseError, match="history.*invalid shape"):
        client.wait_for_completion("p1")


def test_malformed_history_status_fails_clearly() -> None:
    transport = FakeTransport()
    transport.get_responses = [
        {
            "p1": {
                "status": "unexpected",
                "outputs": {"90": {"videos": [{"filename": "out.mp4", "subfolder": "", "type": "output"}]}},
            }
        }
    ]
    client = ComfyUIClient(ComfyUIConfig(), transport=transport, sleep_fn=lambda _seconds: None)

    with pytest.raises(ComfyUIResponseError, match="history.*invalid status"):
        client.wait_for_completion("p1")


def test_history_polling_timeout() -> None:
    transport = FakeTransport()
    transport.get_responses = [{}, {}, {}]
    now = iter([0.0, 0.2, 0.7, 1.2])
    client = ComfyUIClient(
        ComfyUIConfig(timeout_seconds=1, poll_interval_seconds=0.01),
        transport=transport,
        sleep_fn=lambda _seconds: None,
        monotonic_fn=lambda: next(now),
    )

    with pytest.raises(RenderTimeoutError, match="p1"):
        client.wait_for_completion("p1")


def test_history_execution_error_fails_cleanly() -> None:
    transport = FakeTransport()
    transport.get_responses = [
        {
            "p1": {
                "status": {
                    "completed": False,
                    "status_str": "error",
                    "messages": [["execution_error", {"exception_message": "CUDA failed"}]],
                },
                "outputs": {},
            }
        }
    ]
    client = ComfyUIClient(ComfyUIConfig(), transport=transport, sleep_fn=lambda _seconds: None)

    with pytest.raises(RenderExecutionError, match="CUDA failed"):
        client.wait_for_completion("p1")


def test_artifact_discovery_for_image_output() -> None:
    history = {"outputs": {"7": {"images": [{"filename": "frame.png", "subfolder": "shots", "type": "output"}]}}}

    artifacts = discover_artifacts(history)

    assert artifacts == [RenderArtifact("frame.png", "shots", "output", "7")]


def test_artifact_discovery_for_video_gif_and_generic_output_collections() -> None:
    history = {
        "outputs": {
            "8": {
                "videos": [{"filename": "clip.mp4", "subfolder": "video", "type": "output"}],
                "gifs": [{"filename": "preview.gif", "subfolder": "preview", "type": "temp"}],
                "custom_files": [{"filename": "sidecar.webm", "subfolder": "custom", "type": "output"}],
            }
        }
    }

    artifacts = discover_artifacts(history)

    assert {artifact.filename for artifact in artifacts} == {"clip.mp4", "preview.gif", "sidecar.webm"}


def test_artifact_download_preserves_filename_and_extension(tmp_path: Path) -> None:
    transport = FakeTransport()
    transport.bytes_response = b"video"
    client = ComfyUIClient(ComfyUIConfig(), transport=transport)
    artifact = RenderArtifact("clip.webm", "video", "output", "8")

    downloaded = client.download_artifact(artifact, tmp_path)

    assert downloaded.local_path == tmp_path / "clip.webm"
    assert downloaded.local_path.read_bytes() == b"video"
    assert "filename=clip.webm" in transport.calls[0][1]


class FakeRenderClient:
    def __init__(self, *, fail_at: str | None = None) -> None:
        self.fail_at = fail_at
        self.calls: list[str] = []
        self.queued_workflow: dict[str, Any] | None = None

    def upload_image(self, _path: Path) -> UploadedImage:
        self.calls.append("upload")
        if self.fail_at == "upload":
            raise ComfyUIConnectionError("upload failed")
        return UploadedImage("frame.png", "nebula", "input")

    def queue_workflow(self, workflow: dict[str, Any]) -> str:
        self.calls.append("queue")
        self.queued_workflow = workflow
        if self.fail_at == "queue":
            raise ComfyUIResponseError("queue failed")
        return "prompt-1"

    def wait_for_completion(self, _prompt_id: str) -> dict[str, Any]:
        self.calls.append("history")
        if self.fail_at == "history":
            raise RenderExecutionError("history failed")
        return {
            "status": {"completed": True},
            "outputs": {"90": {"videos": [{"filename": "result.mp4", "subfolder": "", "type": "output"}]}},
        }

    def download_artifact(self, artifact: RenderArtifact, destination: Path) -> RenderArtifact:
        self.calls.append("download")
        destination.mkdir(parents=True, exist_ok=True)
        local = destination / artifact.filename
        local.write_bytes(b"video")
        return RenderArtifact(artifact.filename, artifact.subfolder, artifact.type, artifact.node_id, local)


def test_render_service_successful_mocked_end_to_end_flow(tmp_path: Path) -> None:
    keyframe = tmp_path / "keyframe.png"
    keyframe.write_bytes(b"png")
    client = FakeRenderClient()
    statuses: list[str] = []
    service = ComfyRenderService(client, output_root=tmp_path / "outputs")

    result = service.render_shot(
        make_shot(),
        "story:unsafe/name",
        api_workflow(),
        binding_profile(),
        keyframe,
        seed=42,
        output_prefix="nebula-test",
        on_status=statuses.append,
    )

    assert result.prompt_id == "prompt-1"
    assert result.status == "complete"
    assert result.artifacts[0].local_path == tmp_path / "outputs" / "story-unsafe-name" / "shot-001" / "result.mp4"
    assert client.calls == ["upload", "queue", "history", "download"]
    assert client.queued_workflow is not None
    assert client.queued_workflow["101"]["inputs"]["text"] == make_shot().image_prompt
    assert client.queued_workflow["102"]["inputs"]["text"] == make_shot().motion_prompt
    assert client.queued_workflow["45"]["inputs"]["image"] == "nebula/frame.png"
    assert client.queued_workflow["74"]["inputs"]["seed"] == 42
    assert statuses == ["Uploading keyframe...", "Queuing workflow...", "Rendering...", "Downloading output...", "Complete"]


@pytest.mark.parametrize(
    ("fail_at", "expected_calls"),
    [
        ("upload", ["upload"]),
        ("queue", ["upload", "queue"]),
        ("history", ["upload", "queue", "history"]),
    ],
)
def test_render_service_stops_cleanly_on_pipeline_failure(tmp_path: Path, fail_at: str, expected_calls: list[str]) -> None:
    keyframe = tmp_path / "keyframe.png"
    keyframe.write_bytes(b"png")
    client = FakeRenderClient(fail_at=fail_at)
    service = ComfyRenderService(client, output_root=tmp_path / "outputs")

    with pytest.raises((ComfyUIConnectionError, ComfyUIResponseError, RenderExecutionError)):
        service.render_shot(make_shot(), "story-1", api_workflow(), binding_profile(), keyframe)

    assert client.calls == expected_calls
