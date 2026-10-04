# Nebula AI Stories

Nebula AI Stories is a local-first Windows desktop project for creating original short-form AI micro-story concepts. V1 focuses only on the story engine: generating ideas, scoring them with transparent deterministic heuristics, filtering near-duplicate mechanics, selecting a story, planning 2–4 readable shots, and saving/loading the project as JSON.

The target format is roughly 8–15 second vertical stories that feel like believable candid phone videos. They are designed to work visually with little or no dialogue, one simple conflict, a clear payoff, and actions that remain feasible for future image-to-video generation.

## Current V1 workflow

`Ideas → Score → Novelty → Select → Shot Plan`

Implemented now:

- deterministic offline `MockProvider` with varied story families;
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

1. Click **Generate 20 Ideas**.
2. Select a ranked candidate to inspect the story and score breakdown.
3. Click **Create Shot Plan**.
4. Use **Save Project** / **Load Project** for local JSON projects.

## Run tests

```powershell
python -m pytest
```

Tests do not require internet access, Ollama, LM Studio, ComfyUI, or a GPU.

## Folder structure

```text
nebula_ai_stories/
  models/       # story, score, shot, and project data models
  providers/    # text-generation provider interface + offline mock
  story/        # generation, scoring, novelty, prompts, shot planning
  storage/      # JSON project persistence
  ui/           # Tkinter desktop UI
tests/           # pytest coverage
data/            # local project data (ignored except .gitkeep)
outputs/         # future generated outputs (ignored except .gitkeep)
```

## Current limitations

- Scoring and novelty detection are deterministic heuristics, not intelligent LLM evaluation.
- `MockProvider` is deterministic sample content; Ollama and LM Studio providers are future work.
- Shot planning uses a deliberately simple three-shot structure and does not generate media.
- JSON schema version is currently `1`; unsupported versions fail with a handled load error.
- The UI prioritizes function over styling.

The recommended next milestone is local LLM provider integration plus structured story-generation prompts, while keeping the current provider/scorer interfaces intact.
