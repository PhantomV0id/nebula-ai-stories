from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from nebula_ai_stories.comfyui.bindings import load_binding_profile
from nebula_ai_stories.comfyui.client import ComfyUIClient
from nebula_ai_stories.comfyui.config import ComfyUIConfig
from nebula_ai_stories.comfyui.errors import ComfyUIError
from nebula_ai_stories.comfyui.models import BindingProfile, ComfyUIHealth, RenderResult
from nebula_ai_stories.comfyui.service import ComfyRenderService
from nebula_ai_stories.comfyui.workflow import load_api_workflow
from nebula_ai_stories.models.project import StoryProject
from nebula_ai_stories.models.story import StoryCandidate, StoryScore
from nebula_ai_stories.providers.config import DEFAULT_BASE_URLS, ProviderConfig
from nebula_ai_stories.providers.errors import ProviderError
from nebula_ai_stories.providers.factory import create_provider
from nebula_ai_stories.providers.health import ProviderHealth, check_provider_health
from nebula_ai_stories.storage.comfyui_settings_store import ComfyUISettingsStore
from nebula_ai_stories.storage.project_store import ProjectLoadError, ProjectStore
from nebula_ai_stories.storage.settings_store import SettingsStore
from nebula_ai_stories.story.generator import StoryGenerator
from nebula_ai_stories.story.novelty import NoveltyEngine
from nebula_ai_stories.story.planner import ShotPlanner
from nebula_ai_stories.story.scorer import StoryScorer, rank_candidates
from nebula_ai_stories.ui.background import BackgroundWorker
from nebula_ai_stories.ui.render_helpers import (
    build_comfyui_config,
    format_shot_for_render,
    selected_shot,
    shot_choices,
    validate_keyframe_path,
)


class NebulaStoriesApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Nebula AI Stories — ComfyUI Render V1")
        self.root.geometry("1240x840")

        self.generator = StoryGenerator(create_provider(ProviderConfig()))
        self.scorer = StoryScorer()
        self.novelty = NoveltyEngine()
        self.planner = ShotPlanner()
        self.store = ProjectStore()
        self.settings_store = SettingsStore()
        self.comfy_settings_store = ComfyUISettingsStore()
        self.worker = BackgroundWorker(self.root)
        self.project = StoryProject()
        self.story_by_id: dict[str, StoryCandidate] = {}
        self.comfy_workflow: dict[str, object] | None = None
        self.comfy_profile: BindingProfile | None = None
        self.comfy_workflow_path: Path | None = None
        self.comfy_profile_path: Path | None = None
        self.keyframe_path: Path | None = None

        saved = self.settings_store.load()
        self.provider_type_var = tk.StringVar(value=str(saved.provider_type))
        self.base_url_var = tk.StringVar(value=saved.base_url)
        self.model_var = tk.StringVar(value=saved.model)
        self.timeout_var = tk.StringVar(value=f"{saved.timeout_seconds:g}")
        self.temperature_var = tk.StringVar(value=f"{saved.temperature:g}")
        self.max_tokens_var = tk.StringVar(value="" if saved.max_tokens is None else str(saved.max_tokens))
        self.provider_status_var = tk.StringVar(value="Provider: Mock (offline)")

        comfy_saved = self.comfy_settings_store.load()
        self.comfy_url_var = tk.StringVar(value=comfy_saved.base_url)
        self.comfy_timeout_var = tk.StringVar(value=f"{comfy_saved.timeout_seconds:g}")
        self.comfy_poll_var = tk.StringVar(value=f"{comfy_saved.poll_interval_seconds:g}")
        self.comfy_workflow_name_var = tk.StringVar(value="No API workflow loaded")
        self.comfy_profile_name_var = tk.StringVar(value="No binding profile loaded")
        self.keyframe_name_var = tk.StringVar(value="No keyframe selected")
        self.render_shot_var = tk.StringVar(value="")
        self.render_status_var = tk.StringVar(value="ComfyUI render idle")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_initial_provider_status(saved)
        self._restore_comfy_files(comfy_saved)

    def _build_ui(self) -> None:
        controls = ttk.Frame(self.root, padding=8)
        controls.pack(fill="x")
        self.generate_button = ttk.Button(controls, text="Generate 20 Ideas", command=self.generate_ideas)
        self.generate_button.pack(side="left", padx=4)
        ttk.Button(controls, text="Create Shot Plan", command=self.create_shot_plan).pack(side="left", padx=4)
        ttk.Button(controls, text="Save Project", command=self.save_project).pack(side="left", padx=4)
        ttk.Button(controls, text="Load Project", command=self.load_project).pack(side="left", padx=4)

        provider_frame = ttk.LabelFrame(self.root, text="Story Provider", padding=8)
        provider_frame.pack(fill="x", padx=8, pady=(0, 8))

        ttk.Label(provider_frame, text="Provider").grid(row=0, column=0, sticky="w", padx=(0, 4))
        provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=self.provider_type_var,
            values=("mock", "lm_studio", "ollama"),
            state="readonly",
            width=14,
        )
        provider_combo.grid(row=0, column=1, sticky="w", padx=(0, 12))
        provider_combo.bind("<<ComboboxSelected>>", self._on_provider_type_changed)

        ttk.Label(provider_frame, text="Base URL").grid(row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Entry(provider_frame, textvariable=self.base_url_var, width=30).grid(row=0, column=3, sticky="ew", padx=(0, 12))

        ttk.Label(provider_frame, text="Model").grid(row=0, column=4, sticky="w", padx=(0, 4))
        self.model_combo = ttk.Combobox(provider_frame, textvariable=self.model_var, width=24, state="normal")
        self.model_combo.grid(row=0, column=5, sticky="ew")

        ttk.Label(provider_frame, text="Timeout (s)").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=(8, 0))
        ttk.Entry(provider_frame, textvariable=self.timeout_var, width=10).grid(row=1, column=1, sticky="w", pady=(8, 0))

        ttk.Label(provider_frame, text="Temperature").grid(row=1, column=2, sticky="w", padx=(0, 4), pady=(8, 0))
        ttk.Entry(provider_frame, textvariable=self.temperature_var, width=10).grid(row=1, column=3, sticky="w", pady=(8, 0))

        ttk.Label(provider_frame, text="Max tokens").grid(row=1, column=4, sticky="w", padx=(0, 4), pady=(8, 0))
        ttk.Entry(provider_frame, textvariable=self.max_tokens_var, width=10).grid(row=1, column=5, sticky="w", pady=(8, 0))

        self.check_provider_button = ttk.Button(provider_frame, text="Check Provider", command=self.check_provider)
        self.check_provider_button.grid(row=1, column=6, sticky="e", padx=(12, 0), pady=(8, 0))

        ttk.Label(provider_frame, textvariable=self.provider_status_var).grid(
            row=2,
            column=0,
            columnspan=7,
            sticky="w",
            pady=(8, 0),
        )
        provider_frame.columnconfigure(3, weight=1)
        provider_frame.columnconfigure(5, weight=1)

        content = ttk.Panedwindow(self.root, orient="horizontal")
        content.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(content)
        right = ttk.Frame(content)
        content.add(left, weight=2)
        content.add(right, weight=3)

        self.tree = ttk.Treeview(left, columns=("score", "duration", "difficulty"), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Story")
        self.tree.heading("score", text="Score")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("difficulty", text="Difficulty")
        self.tree.column("#0", width=260)
        self.tree.column("score", width=70, anchor="center")
        self.tree.column("duration", width=80, anchor="center")
        self.tree.column("difficulty", width=90, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)
        details_frame = ttk.Frame(notebook)
        shots_frame = ttk.Frame(notebook)
        render_frame = ttk.Frame(notebook, padding=10)
        notebook.add(details_frame, text="Story Details")
        notebook.add(shots_frame, text="Shot Plan")
        notebook.add(render_frame, text="ComfyUI / Render")

        self.details_text = tk.Text(details_frame, wrap="word", padx=10, pady=10)
        self.details_text.pack(fill="both", expand=True)
        self.shots_text = tk.Text(shots_frame, wrap="word", padx=10, pady=10)
        self.shots_text.pack(fill="both", expand=True)
        self._build_render_ui(render_frame)

    def _build_render_ui(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="ComfyUI URL").grid(row=0, column=0, sticky="w")
        self.comfy_url_entry = ttk.Entry(parent, textvariable=self.comfy_url_var, width=36)
        self.comfy_url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(6, 10))
        self.check_comfy_button = ttk.Button(parent, text="Check ComfyUI", command=self.check_comfyui)
        self.check_comfy_button.grid(row=0, column=3, sticky="e")

        ttk.Label(parent, text="Timeout (s)").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.comfy_timeout_entry = ttk.Entry(parent, textvariable=self.comfy_timeout_var, width=10)
        self.comfy_timeout_entry.grid(row=1, column=1, sticky="w", padx=(6, 10), pady=(8, 0))
        ttk.Label(parent, text="Poll interval (s)").grid(row=1, column=2, sticky="e", padx=(10, 6), pady=(8, 0))
        self.comfy_poll_entry = ttk.Entry(parent, textvariable=self.comfy_poll_var, width=10)
        self.comfy_poll_entry.grid(row=1, column=3, sticky="w", pady=(8, 0))

        self.load_workflow_button = ttk.Button(parent, text="Load API Workflow", command=self.load_comfy_workflow)
        self.load_workflow_button.grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Label(parent, textvariable=self.comfy_workflow_name_var).grid(
            row=2, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=(12, 0)
        )

        self.load_profile_button = ttk.Button(parent, text="Load Binding Profile", command=self.load_comfy_profile)
        self.load_profile_button.grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(parent, textvariable=self.comfy_profile_name_var).grid(
            row=3, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=(8, 0)
        )

        self.select_keyframe_button = ttk.Button(parent, text="Select Keyframe", command=self.select_keyframe)
        self.select_keyframe_button.grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Label(parent, textvariable=self.keyframe_name_var).grid(
            row=4, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=(8, 0)
        )

        ttk.Label(parent, text="Shot").grid(row=5, column=0, sticky="w", pady=(12, 0))
        self.render_shot_combo = ttk.Combobox(
            parent,
            textvariable=self.render_shot_var,
            values=(),
            state="readonly",
            width=10,
        )
        self.render_shot_combo.grid(row=5, column=1, sticky="w", padx=(6, 0), pady=(12, 0))
        self.render_shot_combo.bind("<<ComboboxSelected>>", self._on_render_shot_changed)

        self.render_prompt_text = tk.Text(parent, height=12, wrap="word", padx=8, pady=8)
        self.render_prompt_text.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=(8, 0))
        self._set_text(self.render_prompt_text, "Create or load a shot plan, then select a shot to render.")

        self.render_button = ttk.Button(parent, text="Render Selected Shot", command=self.render_selected_shot)
        self.render_button.grid(row=7, column=0, sticky="w", pady=(10, 0))
        ttk.Label(parent, textvariable=self.render_status_var, wraplength=620).grid(
            row=7, column=1, columnspan=3, sticky="w", padx=(10, 0), pady=(10, 0)
        )

        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.rowconfigure(6, weight=1)

    def generate_ideas(self) -> None:
        try:
            config = self._provider_config_from_ui()
        except (ProviderError, ValueError) as exc:
            self._show_provider_error("Story generation failed", exc)
            return

        self._save_settings_safely(config)
        self._set_provider_busy(True, "Generating...")

        def task() -> tuple[ProviderConfig, list[StoryCandidate], list[tuple[StoryCandidate, StoryScore]], dict[str, StoryScore]]:
            generator = StoryGenerator(create_provider(config))
            candidates = generator.generate_candidates(20)
            ranked = rank_candidates(candidates, self.scorer, self.novelty)
            scores = {candidate.id: score for candidate, score in ranked}
            return config, candidates, ranked, scores

        def success(result: tuple[ProviderConfig, list[StoryCandidate], list[tuple[StoryCandidate, StoryScore]], dict[str, StoryScore]]) -> None:
            used_config, candidates, ranked, scores = result
            self.project = StoryProject(generated_candidates=candidates, scores=scores)
            self.story_by_id = {candidate.id: candidate for candidate in candidates}
            self._refresh_tree(ranked)
            self._set_text(self.details_text, "Select a story to inspect its details and score breakdown.")
            self._set_text(self.shots_text, "Create a shot plan after selecting a story.")
            self._refresh_render_shots()
            provider_label = {
                "mock": "Mock (offline)",
                "lm_studio": f"LM Studio / {used_config.model}",
                "ollama": f"Ollama / {used_config.model}",
            }[used_config.provider_type]
            self.provider_status_var.set(f"Generated 20 ideas with {provider_label}")

        self.worker.submit(
            task,
            success,
            lambda exc: self._show_provider_error("Story generation failed", exc),
            lambda: self._set_provider_busy(False),
        )

    def check_provider(self) -> None:
        try:
            config = self._provider_config_from_ui()
        except (ProviderError, ValueError) as exc:
            self._show_provider_error("Provider check failed", exc)
            return

        self._save_settings_safely(config)
        self._set_provider_busy(True, "Checking provider...")

        def success(health: ProviderHealth) -> None:
            lines = [health.message]
            if health.models:
                lines.append("Models:")
                lines.extend(f"- {model}" for model in health.models)
                self.model_combo.configure(values=tuple(health.models))
                if not self.model_var.get().strip():
                    self.model_var.set(health.models[0])
            else:
                self.model_combo.configure(values=())
            self.provider_status_var.set("\n".join(lines))

        self.worker.submit(
            lambda: check_provider_health(config),
            success,
            lambda exc: self._show_provider_error("Provider check failed", exc),
            lambda: self._set_provider_busy(False),
        )

    def _on_provider_type_changed(self, _event: object | None = None) -> None:
        provider_type = self.provider_type_var.get()
        self.base_url_var.set(DEFAULT_BASE_URLS.get(provider_type, ""))
        if provider_type == "mock":
            self.provider_status_var.set("Provider: Mock (offline)")
        else:
            display = "LM Studio" if provider_type == "lm_studio" else "Ollama"
            self.provider_status_var.set(f"Provider: {display} — enter a local model name")
        self.model_combo.configure(values=())

    def _provider_config_from_ui(self) -> ProviderConfig:
        max_tokens_text = self.max_tokens_var.get().strip()
        return ProviderConfig(
            provider_type=self.provider_type_var.get(),
            base_url=self.base_url_var.get(),
            model=self.model_var.get(),
            timeout_seconds=float(self.timeout_var.get()),
            temperature=float(self.temperature_var.get()),
            max_tokens=int(max_tokens_text) if max_tokens_text else None,
        )

    def _comfy_config_from_ui(self) -> ComfyUIConfig:
        return build_comfyui_config(
            self.comfy_url_var.get(),
            self.comfy_timeout_var.get(),
            self.comfy_poll_var.get(),
            self.comfy_workflow_path,
            self.comfy_profile_path,
        )

    def check_comfyui(self) -> None:
        try:
            config = self._comfy_config_from_ui()
        except ValueError as exc:
            self._show_comfy_error("ComfyUI check failed", exc)
            return
        self._save_comfy_settings_safely(config)
        self._set_render_busy(True, "Checking ComfyUI...")

        def success(health: ComfyUIHealth) -> None:
            self.render_status_var.set(health.message)

        self.worker.submit(
            lambda: ComfyUIClient(config).health_check(),
            success,
            lambda exc: self._show_comfy_error("ComfyUI check failed", exc),
            lambda: self._set_render_busy(False),
        )

    def load_comfy_workflow(self) -> None:
        path = filedialog.askopenfilename(
            title="Load ComfyUI API workflow",
            filetypes=[("JSON workflow", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            workflow = load_api_workflow(path)
        except ComfyUIError as exc:
            self._show_comfy_error("Workflow load failed", exc)
            return
        self.comfy_workflow = workflow
        self.comfy_workflow_path = Path(path)
        self.comfy_workflow_name_var.set(self.comfy_workflow_path.name)
        self.render_status_var.set("API workflow loaded")
        self._save_comfy_settings_safely()

    def load_comfy_profile(self) -> None:
        path = filedialog.askopenfilename(
            title="Load ComfyUI binding profile",
            filetypes=[("JSON binding profile", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            profile = load_binding_profile(path)
        except ComfyUIError as exc:
            self._show_comfy_error("Binding profile load failed", exc)
            return
        self.comfy_profile = profile
        self.comfy_profile_path = Path(path)
        self.comfy_profile_name_var.set(f"{self.comfy_profile_path.name} — {profile.name}")
        self.render_status_var.set("Binding profile loaded")
        self._save_comfy_settings_safely()

    def select_keyframe(self) -> None:
        path = filedialog.askopenfilename(
            title="Select keyframe image",
            filetypes=[
                ("Supported images", "*.png *.jpg *.jpeg *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            self.keyframe_path = validate_keyframe_path(path)
        except ValueError as exc:
            self._show_comfy_error("Keyframe selection failed", exc)
            return
        self.keyframe_name_var.set(self.keyframe_path.name)
        self.render_status_var.set("Keyframe selected")

    def _refresh_render_shots(self) -> None:
        choices = shot_choices(self.project.shot_plan)
        self.render_shot_combo.configure(values=choices)
        if not choices:
            self.render_shot_var.set("")
            self._set_text(self.render_prompt_text, "Create or load a shot plan, then select a shot to render.")
            return
        if self.render_shot_var.get() not in choices:
            self.render_shot_var.set(choices[0])
        self._on_render_shot_changed()

    def _on_render_shot_changed(self, _event: object | None = None) -> None:
        try:
            shot = selected_shot(self.project.shot_plan, self.render_shot_var.get())
        except ValueError:
            return
        self._set_text(self.render_prompt_text, format_shot_for_render(shot))

    def render_selected_shot(self) -> None:
        try:
            config = self._comfy_config_from_ui()
            shot = selected_shot(self.project.shot_plan, self.render_shot_var.get())
            keyframe = validate_keyframe_path(self.keyframe_path or "")
            if self.project.selected_story is None:
                raise ValueError("Select a story before rendering a shot")
            if self.comfy_workflow is None:
                raise ValueError("Load a ComfyUI API workflow before rendering")
            if self.comfy_profile is None:
                raise ValueError("Load a ComfyUI binding profile before rendering")
        except (ValueError, ComfyUIError) as exc:
            self._show_comfy_error("Render cannot start", exc)
            return

        self._save_comfy_settings_safely(config)
        self._set_render_busy(True, "Preparing render...")
        workflow = self.comfy_workflow
        profile = self.comfy_profile
        story_id = self.project.selected_story.id

        def progress(message: str) -> None:
            self.root.after(0, lambda value=message: self.render_status_var.set(value))

        def task() -> RenderResult:
            service = ComfyRenderService(ComfyUIClient(config))
            return service.render_shot(
                shot,
                story_id,
                workflow,
                profile,
                keyframe,
                on_status=progress,
            )

        def success(result: RenderResult) -> None:
            paths = [str(artifact.local_path) for artifact in result.artifacts if artifact.local_path]
            self.render_status_var.set("Complete\n" + "\n".join(paths))

        self.worker.submit(
            task,
            success,
            lambda exc: self._show_comfy_error("Render failed", exc),
            lambda: self._set_render_busy(False),
        )

    def _set_render_busy(self, busy: bool, status: str | None = None) -> None:
        state = "disabled" if busy else "normal"
        for button in (
            self.check_comfy_button,
            self.load_workflow_button,
            self.load_profile_button,
            self.select_keyframe_button,
            self.render_button,
        ):
            button.configure(state=state)
        self.render_shot_combo.configure(state="disabled" if busy else "readonly")
        if status is not None:
            self.render_status_var.set(status)

    def _show_comfy_error(self, title: str, exc: Exception) -> None:
        message = str(exc) if isinstance(exc, (ComfyUIError, ValueError)) else f"Unexpected ComfyUI error: {exc}"
        self.render_status_var.set(message)
        messagebox.showerror(title, message)

    def _save_comfy_settings_safely(self, config: ComfyUIConfig | None = None) -> None:
        try:
            self.comfy_settings_store.save(config or self._comfy_config_from_ui())
        except (OSError, ValueError):
            pass

    def _restore_comfy_files(self, config: ComfyUIConfig) -> None:
        if config.workflow_path and config.workflow_path.is_file():
            try:
                self.comfy_workflow = load_api_workflow(config.workflow_path)
                self.comfy_workflow_path = config.workflow_path
                self.comfy_workflow_name_var.set(config.workflow_path.name)
            except ComfyUIError as exc:
                self.render_status_var.set(f"Saved workflow could not be restored: {exc}")
        if config.binding_profile_path and config.binding_profile_path.is_file():
            try:
                self.comfy_profile = load_binding_profile(config.binding_profile_path)
                self.comfy_profile_path = config.binding_profile_path
                self.comfy_profile_name_var.set(f"{config.binding_profile_path.name} — {self.comfy_profile.name}")
            except ComfyUIError as exc:
                self.render_status_var.set(f"Saved binding profile could not be restored: {exc}")

    def _set_initial_provider_status(self, config: ProviderConfig) -> None:
        if config.provider_type == "mock":
            self.provider_status_var.set("Mock Provider: Ready (offline)")
        else:
            display = "LM Studio" if config.provider_type == "lm_studio" else "Ollama"
            self.provider_status_var.set(f"Provider: {display} — settings restored")

    def _set_provider_busy(self, busy: bool, status: str | None = None) -> None:
        state = "disabled" if busy else "normal"
        self.generate_button.configure(state=state)
        self.check_provider_button.configure(state=state)
        if status is not None:
            self.provider_status_var.set(status)

    def _show_provider_error(self, title: str, exc: Exception) -> None:
        message = str(exc) if isinstance(exc, (ProviderError, ValueError)) else f"Unexpected provider error: {exc}"
        self.provider_status_var.set(message)
        messagebox.showerror(title, message)

    def _save_settings_safely(self, config: ProviderConfig | None = None) -> None:
        try:
            self.settings_store.save(config or self._provider_config_from_ui())
        except (OSError, ValueError):
            pass

    def _on_close(self) -> None:
        self._save_settings_safely()
        self._save_comfy_settings_safely()
        self.root.destroy()

    def _refresh_tree(self, ranked: list[tuple[StoryCandidate, object]] | None = None) -> None:
        self.tree.delete(*self.tree.get_children())
        if ranked is None:
            ranked = sorted(
                ((story, self.project.scores[story.id]) for story in self.project.generated_candidates if story.id in self.project.scores),
                key=lambda item: item[1].overall_score,
                reverse=True,
            )
        for candidate, score in ranked:
            premise = candidate.premise if len(candidate.premise) <= 70 else f"{candidate.premise[:67]}..."
            self.tree.insert(
                "",
                "end",
                iid=candidate.id,
                text=f"{candidate.title}\n{premise}",
                values=(f"{score.overall_score:.2f}", f"{candidate.estimated_duration_seconds:.1f}s", candidate.generation_difficulty),
            )

    def _on_select(self, _event: object | None = None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        story = self.story_by_id.get(selection[0])
        if story is None:
            return
        previous_story = self.project.selected_story
        story_changed = previous_story is None or previous_story.id != story.id
        if story_changed:
            self.project.shot_plan = []
            self._set_text(self.shots_text, "Create a shot plan after selecting a story.")
            self._refresh_render_shots()
        self.project.selected_story = story
        score = self.project.scores.get(story.id)
        lines = [
            story.title,
            "",
            f"Premise: {story.premise}",
            f"Hook: {story.hook}",
            f"Problem: {story.problem}",
            f"Action: {story.action}",
            f"Twist: {story.twist}",
            f"Payoff: {story.payoff}",
            f"Mechanics: {', '.join(story.story_mechanics)}",
            f"Tags: {', '.join(story.tags)}",
        ]
        if score:
            lines.extend(
                [
                    "",
                    "Score breakdown:",
                    f"  Hook: {score.hook_strength:.2f}",
                    f"  Visual clarity: {score.visual_clarity:.2f}",
                    f"  Conflict: {score.conflict_strength:.2f}",
                    f"  Payoff: {score.payoff_strength:.2f}",
                    f"  Emotion: {score.emotional_strength:.2f}",
                    f"  Generation feasibility: {score.generation_feasibility:.2f}",
                    f"  Novelty: {score.novelty:.2f}",
                    f"  Overall: {score.overall_score:.2f}",
                ]
            )
        self._set_text(self.details_text, "\n".join(lines))

    def create_shot_plan(self) -> None:
        story = self.project.selected_story
        if story is None:
            messagebox.showinfo("Select a story", "Select a story before creating a shot plan.")
            return
        self.project.shot_plan = self.planner.plan(story)
        blocks: list[str] = []
        for shot in self.project.shot_plan:
            blocks.append(
                "\n".join(
                    [
                        f"SHOT {shot.shot_index} — {shot.duration_seconds:.1f}s — {shot.story_function}",
                        f"Visual: {shot.visual_description}",
                        f"Image prompt: {shot.image_prompt}",
                        f"Motion prompt: {shot.motion_prompt}",
                        f"Continuity: {shot.continuity_notes}",
                    ]
                )
            )
        self._set_text(self.shots_text, "\n\n".join(blocks))
        self._refresh_render_shots()

    def save_project(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Nebula AI Stories project",
            defaultextension=".json",
            filetypes=[("JSON project", "*.json")],
            initialdir=str(Path.cwd() / "data"),
        )
        if not path:
            return
        try:
            self.store.save(self.project, path)
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))

    def load_project(self) -> None:
        path = filedialog.askopenfilename(
            title="Load Nebula AI Stories project",
            filetypes=[("JSON project", "*.json"), ("All files", "*.*")],
            initialdir=str(Path.cwd() / "data"),
        )
        if not path:
            return
        try:
            self.project = self.store.load(path)
        except ProjectLoadError as exc:
            messagebox.showerror("Load failed", str(exc))
            return
        self.story_by_id = {candidate.id: candidate for candidate in self.project.generated_candidates}
        self._refresh_tree()
        if self.project.selected_story and self.project.selected_story.id in self.story_by_id:
            self.tree.selection_set(self.project.selected_story.id)
            self.tree.focus(self.project.selected_story.id)
            self._on_select()
        if self.project.shot_plan:
            blocks = [
                f"SHOT {shot.shot_index} — {shot.duration_seconds:.1f}s — {shot.story_function}\n"
                f"Visual: {shot.visual_description}\nImage prompt: {shot.image_prompt}\n"
                f"Motion prompt: {shot.motion_prompt}\nContinuity: {shot.continuity_notes}"
                for shot in self.project.shot_plan
            ]
            self._set_text(self.shots_text, "\n\n".join(blocks))
        self._refresh_render_shots()

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    NebulaStoriesApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
