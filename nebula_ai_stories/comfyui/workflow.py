from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nebula_ai_stories.comfyui.errors import WorkflowFormatError


def validate_api_workflow(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or not data:
        raise WorkflowFormatError("ComfyUI API workflow must be a non-empty JSON object keyed by node IDs")
    if isinstance(data.get("nodes"), list) or "links" in data or "last_node_id" in data:
        raise WorkflowFormatError(
            "This appears to be a ComfyUI UI workflow. Export/save the workflow in API format."
        )
    for node_id, node in data.items():
        if not isinstance(node_id, str) or not node_id.strip():
            raise WorkflowFormatError("ComfyUI API workflow node IDs must be non-empty strings")
        if not isinstance(node, dict):
            raise WorkflowFormatError(f"ComfyUI API workflow node {node_id} must be a JSON object")
        if not isinstance(node.get("class_type"), str) or not node["class_type"].strip():
            raise WorkflowFormatError(f"ComfyUI API workflow node {node_id} is missing class_type")
        if not isinstance(node.get("inputs"), dict):
            raise WorkflowFormatError(f"ComfyUI API workflow node {node_id} is missing inputs")
    return data


def load_api_workflow(path: str | Path) -> dict[str, Any]:
    workflow_path = Path(path)
    try:
        data = json.loads(workflow_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise WorkflowFormatError(f"Could not read ComfyUI workflow: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowFormatError(f"ComfyUI workflow contains malformed JSON: {exc}") from exc
    return validate_api_workflow(data)
