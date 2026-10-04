from __future__ import annotations

import threading
from pathlib import Path

from nebula_ai_stories.providers.config import ProviderConfig
from nebula_ai_stories.storage.settings_store import SettingsStore
from nebula_ai_stories.ui.background import BackgroundWorker


def test_settings_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "provider-settings.json"
    store = SettingsStore(path)
    config = ProviderConfig(
        provider_type="ollama",
        base_url="http://127.0.0.1:11434",
        model="qwen3:8b",
        timeout_seconds=45,
        temperature=0.6,
        max_tokens=2500,
    )

    store.save(config)
    loaded = store.load()

    assert loaded == config


def test_malformed_settings_fall_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "provider-settings.json"
    path.write_text("{not json", encoding="utf-8")

    loaded = SettingsStore(path).load()

    assert loaded == ProviderConfig()


def test_background_worker_runs_task_off_calling_thread() -> None:
    completed = threading.Event()
    main_thread_id = threading.get_ident()
    observed: dict[str, int] = {}

    class FakeRoot:
        def after(self, _delay: int, callback: object) -> None:
            callback()  # type: ignore[operator]

    worker = BackgroundWorker(FakeRoot())

    def task() -> str:
        observed["task_thread"] = threading.get_ident()
        return "ok"

    def success(value: str) -> None:
        assert value == "ok"
        completed.set()

    worker.submit(task, success, lambda exc: (_ for _ in ()).throw(exc))

    assert completed.wait(2)
    assert observed["task_thread"] != main_thread_id
