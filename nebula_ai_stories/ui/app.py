from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from nebula_ai_stories.models.project import StoryProject
from nebula_ai_stories.models.story import StoryCandidate, StoryScore
from nebula_ai_stories.providers.config import DEFAULT_BASE_URLS, ProviderConfig
from nebula_ai_stories.providers.errors import ProviderError
from nebula_ai_stories.providers.factory import create_provider
from nebula_ai_stories.providers.health import ProviderHealth, check_provider_health
from nebula_ai_stories.storage.project_store import ProjectLoadError, ProjectStore
from nebula_ai_stories.storage.settings_store import SettingsStore
from nebula_ai_stories.story.generator import StoryGenerator
from nebula_ai_stories.story.novelty import NoveltyEngine
from nebula_ai_stories.story.planner import ShotPlanner
from nebula_ai_stories.story.scorer import StoryScorer, rank_candidates
from nebula_ai_stories.ui.background import BackgroundWorker


class NebulaStoriesApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Nebula AI Stories — Local AI Providers V1")
        self.root.geometry("1180x780")

        self.generator = StoryGenerator(create_provider(ProviderConfig()))
        self.scorer = StoryScorer()
        self.novelty = NoveltyEngine()
        self.planner = ShotPlanner()
        self.store = ProjectStore()
        self.settings_store = SettingsStore()
        self.worker = BackgroundWorker(self.root)
        self.project = StoryProject()
        self.story_by_id: dict[str, StoryCandidate] = {}

        saved = self.settings_store.load()
        self.provider_type_var = tk.StringVar(value=str(saved.provider_type))
        self.base_url_var = tk.StringVar(value=saved.base_url)
        self.model_var = tk.StringVar(value=saved.model)
        self.timeout_var = tk.StringVar(value=f"{saved.timeout_seconds:g}")
        self.temperature_var = tk.StringVar(value=f"{saved.temperature:g}")
        self.max_tokens_var = tk.StringVar(value="" if saved.max_tokens is None else str(saved.max_tokens))
        self.provider_status_var = tk.StringVar(value="Provider: Mock (offline)")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_initial_provider_status(saved)

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
        notebook.add(details_frame, text="Story Details")
        notebook.add(shots_frame, text="Shot Plan")

        self.details_text = tk.Text(details_frame, wrap="word", padx=10, pady=10)
        self.details_text.pack(fill="both", expand=True)
        self.shots_text = tk.Text(shots_frame, wrap="word", padx=10, pady=10)
        self.shots_text.pack(fill="both", expand=True)

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
