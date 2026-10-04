from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from nebula_ai_stories.models.project import StoryProject
from nebula_ai_stories.models.story import StoryCandidate
from nebula_ai_stories.providers.mock_provider import MockProvider
from nebula_ai_stories.storage.project_store import ProjectLoadError, ProjectStore
from nebula_ai_stories.story.generator import StoryGenerator
from nebula_ai_stories.story.novelty import NoveltyEngine
from nebula_ai_stories.story.planner import ShotPlanner
from nebula_ai_stories.story.scorer import StoryScorer, rank_candidates


class NebulaStoriesApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Nebula AI Stories — Story Engine V1")
        self.root.geometry("1180x780")

        self.generator = StoryGenerator(MockProvider())
        self.scorer = StoryScorer()
        self.novelty = NoveltyEngine()
        self.planner = ShotPlanner()
        self.store = ProjectStore()
        self.project = StoryProject()
        self.story_by_id: dict[str, StoryCandidate] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        controls = ttk.Frame(self.root, padding=8)
        controls.pack(fill="x")
        ttk.Button(controls, text="Generate 20 Ideas", command=self.generate_ideas).pack(side="left", padx=4)
        ttk.Button(controls, text="Create Shot Plan", command=self.create_shot_plan).pack(side="left", padx=4)
        ttk.Button(controls, text="Save Project", command=self.save_project).pack(side="left", padx=4)
        ttk.Button(controls, text="Load Project", command=self.load_project).pack(side="left", padx=4)

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
        candidates = self.generator.generate_candidates(20)
        ranked = rank_candidates(candidates, self.scorer, self.novelty)
        scores = {candidate.id: score for candidate, score in ranked}
        self.project = StoryProject(generated_candidates=candidates, scores=scores)
        self.story_by_id = {candidate.id: candidate for candidate in candidates}
        self._refresh_tree(ranked)
        self._set_text(self.details_text, "Select a story to inspect its details and score breakdown.")
        self._set_text(self.shots_text, "Create a shot plan after selecting a story.")

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

