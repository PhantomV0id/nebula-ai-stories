# Nebula AI Stories

Nebula AI Stories is a local-first Windows desktop project for creating original short-form AI micro-story concepts. The current version supports deterministic offline story ideas plus optional local LLM generation through LM Studio or Ollama. Generated ideas are validated, scored, filtered for novelty, ranked, selected, and converted into short shot plans.

The target format is roughly 8–15 second vertical stories that feel like believable candid phone videos. They are designed to work visually with little or no dialogue, one simple conflict, a clear payoff, and actions that remain feasible for future image-to-video generation.

## Current workflow

`Local LLM / Mock → Structured Ideas → Validate → Score → Novelty → Select → Shot Plan`

Implemented now:

- deterministic offline `MockProvider` with varied story families;
- LM Studio provider using the local OpenAI-compatible `POST /v1/chat/completions` endpoint;
- Ollama provider using local `POST /api/chat`;
- configurable base URL, model, timeout, temperature, and max token budget;
- robust extraction of JSON arrays from plain JSON, fenced JSON, or small model preambles;
- explicit errors for unavailable local servers and malformed model output, with no silent Mock fallback;
- validated `StoryCandidate`, `StoryScore`, `Shot`, and `StoryProject` models;
- exact-count story generation;
- replaceable heuristic story scoring and ranking;
- deterministic story-mechanic novelty detection;
- 3-shot planning with separate image and motion prompts;
- local JSON project save/load with schema validation and user-facing load errors;
- lightweight Tkinter desktop UI for the full V1 workflow;
- pytest coverage for validation, ranking, novelty, planning, and storage.

## Planned future workflow — NOT IMPLEMENTED

`Story Engine → Keyframes → ComfyUI → WAN 2.2 I2V → QC → FFmpeg Assembly → Audio → Metadata`

ComfyUI integration, WAN/video generation, render queues, vision QC, retries, FFmpeg assembly, audio/SFX, upload automation, analytics, and automated batch rendering are intentionally **not implemented** in V1.

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
2. For LM Studio or Ollama, enter the exact local model name. The default URLs are `http://127.0.0.1:1234` and `http://127.0.0.1:11434` respectively.
3. Click **Generate 20 Ideas**.
4. Select a ranked candidate to inspect the story and score breakdown.
5. Click **Create Shot Plan**.
6. Use **Save Project** / **Load Project** for local JSON projects.

The application does not contact OpenAI or any cloud service. `MockProvider` remains fully offline. LM Studio and Ollama failures are shown directly and do not trigger an automatic fallback.

## Run tests

```powershell
python -m pytest
```

Tests do not require internet access, a running Ollama/LM Studio server, ComfyUI, or a GPU. Provider HTTP behavior is tested with deterministic fake responses.

## Folder structure

```text
nebula_ai_stories/
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
- Local model discovery and automatic model selection are not implemented; enter the installed model name manually.
- Shot planning uses a deliberately simple three-shot structure and does not generate media.
- JSON schema version is currently `1`; unsupported versions fail with a handled load error.
- The UI prioritizes function over styling.

The recommended next milestone is local LLM provider integration plus structured story-generation prompts, while keeping the current provider/scorer interfaces intact.
