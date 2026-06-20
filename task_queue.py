"""Background task queue with cancellation and retry support."""

from __future__ import annotations

import queue
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class Task:
    task_id: str
    label: str
    fn: Callable[[], Any]
    retries: int = 0


class TaskQueue:
    """Executes work on a background worker thread."""

    def __init__(self):
        self._q: queue.Queue[Task] = queue.Queue()
        self._cancelled: set[str] = set()
        self._latest_task: Optional[Task] = None
        self._running = True
        self._callbacks: Dict[str, Callable[[str, Any], None]] = {}
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def register_callback(self, key: str, callback: Callable[[str, Any], None]) -> None:
        self._callbacks[key] = callback

    def submit(self, label: str, fn: Callable[[], Any]) -> str:
        task = Task(task_id=str(uuid.uuid4()), label=label, fn=fn)
        self._latest_task = task
        self._q.put(task)
        self._emit("queued", {"task_id": task.task_id, "label": label})
        return task.task_id

    def cancel(self, task_id: str) -> None:
        self._cancelled.add(task_id)
        self._emit("cancelled", {"task_id": task_id})

    def retry_latest(self) -> Optional[str]:
        if not self._latest_task:
            return None
        retry_task = Task(
            task_id=str(uuid.uuid4()),
            label=f"{self._latest_task.label} (retry)",
            fn=self._latest_task.fn,
            retries=self._latest_task.retries + 1,
        )
        self._latest_task = retry_task
        self._q.put(retry_task)
        self._emit("queued", {"task_id": retry_task.task_id, "label": retry_task.label})
        return retry_task.task_id

    def shutdown(self) -> None:
        self._running = False
        self._q.put(Task(task_id="__stop__", label="stop", fn=lambda: None))

    def _run(self) -> None:
        while self._running:
            task = self._q.get()
            if task.task_id == "__stop__":
                break
            if task.task_id in self._cancelled:
                self._q.task_done()
                continue
            self._emit("started", {"task_id": task.task_id, "label": task.label})
            try:
                result = task.fn()
                if task.task_id not in self._cancelled:
                    self._emit("completed", {"task_id": task.task_id, "result": result})
            except Exception as exc:
                self._emit("failed", {"task_id": task.task_id, "error": str(exc)})
            finally:
                self._q.task_done()

    def _emit(self, event_name: str, payload: Any) -> None:
        for callback in self._callbacks.values():
            try:
                callback(event_name, payload)
            except Exception:
                continue
