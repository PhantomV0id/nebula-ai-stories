from __future__ import annotations

from typing import Any

from nebula_ai_stories.comfyui.errors import ComfyUIResponseError
from nebula_ai_stories.comfyui.models import RenderArtifact


def discover_artifacts(history_entry: dict[str, Any]) -> list[RenderArtifact]:
    outputs = history_entry.get("outputs")
    if not isinstance(outputs, dict):
        raise ComfyUIResponseError("ComfyUI history is missing an outputs object")
    artifacts: list[RenderArtifact] = []
    seen: set[tuple[str, str, str, str]] = set()
    for node_id, node_output in outputs.items():
        if not isinstance(node_output, dict):
            continue
        for collection in node_output.values():
            if not isinstance(collection, list):
                continue
            for item in collection:
                if not isinstance(item, dict) or not isinstance(item.get("filename"), str):
                    continue
                filename = item["filename"].strip()
                if not filename:
                    continue
                subfolder = item.get("subfolder", "")
                artifact_type = item.get("type", "output")
                if not isinstance(subfolder, str):
                    subfolder = ""
                if not isinstance(artifact_type, str):
                    artifact_type = "output"
                key = (filename, subfolder, artifact_type, str(node_id))
                if key in seen:
                    continue
                seen.add(key)
                artifacts.append(RenderArtifact(filename, subfolder, artifact_type, str(node_id)))
    return artifacts
