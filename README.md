# Nebula AI Stories

Nebula AI Stories is a local-first Windows desktop project for creating original short-form AI micro-story concepts and validating the first media-generation step. The current version supports deterministic offline story ideas, optional local LLM generation through LM Studio or Ollama, shot planning, and single-shot rendering through a user-supplied ComfyUI API workflow.

The target format is roughly 8–15 second vertical stories that feel like believable candid phone videos. They are designed to work visually with little or no dialogue, one simple conflict, a clear payoff, and actions that remain feasible for future image-to-video generation.

## Current workflow

`Local LLM / Mock → Structured Ideas → Validate → Score → Novelty → Select → Shot Plan → Manual Keyframe → ComfyUI Single-Shot Render`

Implemented now:

- deterministic offline `MockProvider` with varied story families;
- LM Studio provider using the local OpenAI-compatible `POST /v1/chat/completions` endpoint;
- Ollama provider using local `POST /api/chat`;
- configurable base URL, model, timeout, temperature, and max token budget;
- **Check Provider** health check with LM Studio/Ollama model discovery;
- model dropdown population from discovered local models while preserving manual model entry;
- robust extraction of JSON arrays from plain JSON, fenced JSON, or small model preambles;
- exactly one automatic repair request when model output is malformed, wrong-count, or fails StoryCandidate validation;
- deterministic local ID normalization (`story-001`, `story-002`, ...) so model IDs cannot collide in the UI;
- explicit errors for unavailable local servers and malformed model output, with no silent Mock fallback;
- provider generation and health checks run on a background worker so the Tkinter UI remains responsive;
- local provider settings persist in ignored `data/provider_settings.json` and malformed settings safely fall back to defaults;
- validated `StoryCandidate`, `StoryScore`, `Shot`, and `StoryProject` models;
- exact-count story generation;
- replaceable heuristic story scoring and ranking;
- deterministic story-mechanic novelty detection;
- 3-shot planning with separate image and motion prompts;
- local JSON project save/load with schema validation and user-facing load errors;
- lightweight Tkinter desktop UI for the full V1 workflow;
- generic ComfyUI client for health checks, image upload, workflow queueing, history polling, artifact discovery, and artifact download;
- API-workflow validation with explicit rejection of obvious normal/UI workflow JSON;
- explicit workflow binding profiles that map Nebula semantic values to user-owned ComfyUI node IDs and input names;
- manual PNG/JPG/JPEG/WEBP keyframe selection and upload through `/upload/image`;
- single selected-shot rendering through `/prompt` + `/history/{prompt_id}` with configurable timeout/polling;
- generic image/GIF/video/descriptor-shaped artifact discovery and local saving under `outputs/<story-id>/shot-NNN/`;
- ComfyUI operations run through the existing background worker so Tkinter remains responsive;
- local ComfyUI settings persist in ignored `data/comfyui_settings.json`;
- pytest coverage for validation, ranking, novelty, planning, and storage.

## ComfyUI setup

Start your normal local ComfyUI installation. A common source-install command from the ComfyUI directory is:

```powershell
python main.py --listen 127.0.0.1 --port 8188
```

Nebula defaults to:

```text
http://127.0.0.1:8188
```

Use **Check ComfyUI** in the **ComfyUI / Render** tab to call `GET /system_stats` without starting a render.

### API workflow is required

ComfyUI's normal visual/editor workflow JSON is **not** the same thing as the API prompt JSON accepted by `/prompt`. Nebula deliberately does not try to convert visual workflow files because custom nodes and frontend metadata make automatic conversion unreliable.

Export/save your workflow from ComfyUI in **API format** (often shown as **Save (API Format)** or an API/export option when developer features are enabled). The resulting JSON should be an object keyed by node IDs, where each node has at least `class_type` and `inputs`.

If Nebula sees obvious UI-workflow fields such as `nodes`, `links`, or `last_node_id`, it stops with:

> This appears to be a ComfyUI UI workflow. Export/save the workflow in API format.

### Binding profiles

Nebula never invents or hard-codes WAN node IDs. A separate binding profile tells Nebula exactly which node/input in **your** API workflow receives each semantic value.

Example template only — replace every placeholder with IDs/input names from your actual workflow:

```json
{
  "name": "my-local-i2v-workflow",
  "bindings": {
    "image_prompt": {
      "node_id": "YOUR_IMAGE_PROMPT_NODE_ID",
      "input_name": "text"
    },
    "motion_prompt": {
      "node_id": "YOUR_MOTION_PROMPT_NODE_ID",
      "input_name": "text"
    },
    "input_image": {
      "node_id": "YOUR_LOAD_IMAGE_NODE_ID",
      "input_name": "image"
    },
    "seed": {
      "node_id": "YOUR_SEED_NODE_ID",
      "input_name": "seed"
    },
    "output_prefix": {
      "node_id": "YOUR_OUTPUT_NODE_ID",
      "input_name": "filename_prefix"
    }
  }
}
```

Supported semantic bindings are `image_prompt`, `motion_prompt`, `negative_prompt`, `input_image`, `seed`, and `output_prefix`. Not every optional binding has to be present, but any binding that is present must point to a real node and existing input. Nebula deep-copies the workflow before patching and never silently modifies unrelated inputs.

## Render one shot

1. Generate/select a story and click **Create Shot Plan**.
2. Open **ComfyUI / Render** and confirm the local URL with **Check ComfyUI**.
3. Click **Load API Workflow** and select the API-format JSON exported from ComfyUI.
4. Click **Load Binding Profile** and select the matching profile JSON.
5. Click **Select Keyframe** and choose an existing PNG/JPG/JPEG/WEBP image.
6. Choose shot 1/2/3 (or whichever indexes exist in the loaded shot plan) and review its separate image/motion prompts.
7. Click **Render Selected Shot**. Nebula uploads the keyframe, patches only configured bindings, queues the prompt, polls history without busy-looping, discovers output artifacts, and downloads them locally.

Render outputs are saved predictably under:

```text
outputs/
  <story-id>/
    shot-001/
      <actual-comfyui-output.ext>
```

The real output extension is preserved and unrelated existing files are not overwritten.

## Planned future workflow — NOT IMPLEMENTED

`Story Engine → Automatic Keyframes → ComfyUI/WAN Batch Render → Vision QC/Retry → FFmpeg Assembly → Audio → Metadata/Upload`

The current ComfyUI milestone renders **one selected shot only**. Automatic keyframe generation, batch rendering, vision QC, automatic rerenders, final multi-shot FFmpeg assembly, audio/SFX, metadata, upload automation, and analytics are intentionally **not implemented** yet.

## Installation

Python 3.11+ is required. The V1 runtime uses only the Python standard library.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

For this repository's current offline V1, you can also run directly from the project folder if `pytest` is already installed.

## Run the desktop app

```powershell
python -m nebula_ai_stories
```

In the app:

1. Choose `mock`, `lm_studio`, or `ollama` in **Story Provider**.
2. Click **Check Provider** to test the selected local server without generating stories. LM Studio uses `/v1/models`; Ollama uses `/api/tags`.
3. If models are discovered, choose one from the model dropdown, or type a model name manually. The default URLs are `http://127.0.0.1:1234` and `http://127.0.0.1:11434` respectively.
4. Click **Generate 20 Ideas**. The network/model work runs outside the Tk main thread and the provider controls are temporarily disabled while it runs.
5. If the first model response is invalid, Nebula sends exactly one repair request to the same provider/model and validates the full corrected batch again.
6. Select a ranked candidate to inspect the story and score breakdown, then click **Create Shot Plan**.
7. Use **Save Project** / **Load Project** for local JSON projects.

The application does not contact OpenAI or any cloud service. `MockProvider` remains fully offline. LM Studio and Ollama failures are shown directly and do not trigger an automatic fallback.
Provider settings are restored on startup and saved locally on provider operations/app close. No passwords or API keys are stored.

## Run tests

```powershell
python -m pytest
```

Tests do not require internet access, a running Ollama/LM Studio server, ComfyUI, a GPU, or WAN models. Provider and ComfyUI HTTP behavior is tested with deterministic fake responses.

## Folder structure

```text
nebula_ai_stories/
  comfyui/      # workflow/profile adapter, client, artifacts, render service
  models/       # story, score, shot, and project data models
  providers/    # config, HTTP/JSON handling, Mock, LM Studio, Ollama
  story/        # generation prompts, scoring, novelty, shot planning
  storage/      # JSON project persistence
  ui/           # Tkinter desktop UI
tests/           # pytest coverage
data/            # local project data (ignored except .gitkeep)
outputs/         # future generated outputs (ignored except .gitkeep)
```

## Current limitations

- Scoring and novelty detection are deterministic heuristics, not intelligent LLM evaluation.
- LM Studio/Ollama model quality depends on the local model selected by the user.
- Model discovery depends on the local server exposing its standard model-list endpoint; manual model entry remains available.
- Shot planning uses a deliberately simple three-shot structure and does not generate media.
- ComfyUI V1 requires a manually selected keyframe plus a user-supplied API workflow and matching binding profile.
- A real WAN/custom-node workflow is not bundled or assumed; successful rendering depends on the user's local ComfyUI workflow and installed nodes/models.
- Only one shot is rendered at a time; no automatic QC or final video assembly exists yet.
- JSON schema version is currently `1`; unsupported versions fail with a handled load error.
- The UI prioritizes function over styling.

The recommended next milestone after validating a real local workflow is **automatic keyframe generation plus multi-shot render orchestration/QC**.
