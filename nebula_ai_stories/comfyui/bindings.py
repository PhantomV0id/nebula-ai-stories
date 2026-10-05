from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from nebula_ai_stories.comfyui.errors import WorkflowBindingError, WorkflowFormatError
from nebula_ai_stories.comfyui.models import BindingProfile, WorkflowBinding
from nebula_ai_stories.comfyui.workflow import validate_api_workflow


SUPPORTED_BINDINGS = {
    "image_prompt",
    "motion_prompt",
    "negative_prompt",
    "input_image",
    "seed",
    "output_prefix",
}


def load_binding_profile(path: str | Path) -> BindingProfile:
    profile_path = Path(path)
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise WorkflowBindingError(f"Could not read binding profile: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowBindingError(f"Binding profile contains malformed JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkflowBindingError("Binding profile must be a JSON object")
    name = data.get("name")
    raw_bindings = data.get("bindings")
    if not isinstance(name, str) or not name.strip():
        raise WorkflowBindingError("Binding profile requires a non-empty name")
    if not isinstance(raw_bindings, dict):
        raise WorkflowBindingError("Binding profile requires a bindings object")
    bindings: dict[str, WorkflowBinding] = {}
    for semantic_name, raw in raw_bindings.items():
        if semantic_name not in SUPPORTED_BINDINGS:
            raise WorkflowBindingError(f"Unsupported binding name: {semantic_name}")
        if not isinstance(raw, dict):
            raise WorkflowBindingError(f"Binding {semantic_name} must be an object")
        node_id = raw.get("node_id")
        input_name = raw.get("input_name")
        if not isinstance(node_id, (str, int)) or not isinstance(input_name, str):
            raise WorkflowBindingError(f"Binding {semantic_name} requires node_id and input_name")
        try:
            bindings[semantic_name] = WorkflowBinding(str(node_id), input_name)
        except ValueError as exc:
            raise WorkflowBindingError(f"Binding {semantic_name} is invalid: {exc}") from exc
    return BindingProfile(name.strip(), bindings)


def patch_workflow(
    workflow: dict[str, Any],
    profile: BindingProfile,
    values: dict[str, Any],
) -> dict[str, Any]:
    validate_api_workflow(workflow)
    patched = copy.deepcopy(workflow)
    for semantic_name, binding in profile.bindings.items():
        node = patched.get(binding.node_id)
        if node is None:
            raise WorkflowBindingError(
                f"Binding {semantic_name} references missing node {binding.node_id}"
            )
        inputs = node.get("inputs")
        if not isinstance(inputs, dict) or binding.input_name not in inputs:
            raise WorkflowBindingError(
                f"Binding {semantic_name} references missing input {binding.input_name} on node {binding.node_id}"
            )
        if semantic_name in values and values[semantic_name] is not None:
            inputs[binding.input_name] = values[semantic_name]
    return patched
