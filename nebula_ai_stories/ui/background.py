from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, Protocol, TypeVar


T = TypeVar("T")


class AfterRoot(Protocol):
    def after(self, delay_ms: int, callback: Callable[[], Any]) -> Any: ...


class BackgroundWorker:
    """Run blocking local provider work off the Tk thread and marshal callbacks through root.after."""

    def __init__(self, root: AfterRoot) -> None:
        self.root = root

    def submit(
        self,
        task: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[Exception], None],
        on_finally: Callable[[], None] | None = None,
    ) -> threading.Thread:
        def finish(callback: Callable[[], None]) -> None:
            def wrapped() -> None:
                try:
                    callback()
                finally:
                    if on_finally is not None:
                        on_finally()

            self.root.after(0, wrapped)

        def work() -> None:
            try:
                result = task()
            except Exception as exc:
                finish(lambda exc=exc: on_error(exc))
            else:
                finish(lambda result=result: on_success(result))

        thread = threading.Thread(target=work, daemon=True, name="nebula-provider-worker")
        thread.start()
        return thread
