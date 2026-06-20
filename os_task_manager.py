"""Task Manager database helper, storing priority, tags, status, and completion."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from logger import get_logger

_log = get_logger("os_task_manager")


class OSTaskManager:
    """Manages system-wide task structures with priorities, due dates, and dependencies."""

    def __init__(self, storage_path: str = "tasks.json"):
        self.storage_path = Path(storage_path)
        self._tasks: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                self._tasks = json.loads(self.storage_path.read_text(encoding="utf-8"))
            except Exception:
                self._tasks = []

    def save(self) -> None:
        try:
            self.storage_path.write_text(json.dumps(self._tasks, indent=2), encoding="utf-8")
        except Exception as e:
            _log.error("Failed to save tasks database: %s", str(e))

    def add_task(self, title: str, priority: int = 5, tags: Optional[List[str]] = None, due_date: str = "") -> Dict[str, Any]:
        cleaned = (title or "").strip()
        if not cleaned:
            return {"success": False, "error": "Task title required"}

        task = {
            "id": len(self._tasks) + 1,
            "title": cleaned,
            "priority": int(priority),
            "tags": tags or [],
            "due_date": (due_date or "").strip(),
            "status": "pending",
            "completion_pct": 0,
        }
        self._tasks.append(task)
        self.save()
        _log.info("Created task: %s (Priority: %d)", cleaned, priority)
        return {"success": True, "task": task}

    def update_task_progress(self, task_id: int, pct: int) -> Dict[str, Any]:
        for task in self._tasks:
            if task.get("id") == int(task_id):
                task["completion_pct"] = min(100, max(0, int(pct)))
                if task["completion_pct"] == 100:
                    task["status"] = "completed"
                self.save()
                return {"success": True, "task": task}
        return {"success": False, "error": f"Task ID {task_id} not found"}

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        return [t for t in self._tasks if t.get("status") == "pending"]
