"""Persistent memory manager for conversations and actions."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List


class MemoryManager:
    """Stores messages and actions in memory.json."""

    def __init__(self, file_path: str = "memory.json"):
        self.file_path = Path(file_path)
        self._ensure_file()

    def add_user_message(self, text: str) -> None:
        self._add_message("user", text)

    def add_assistant_message(self, text: str) -> None:
        self._add_message("assistant", text)

    def add_action(self, action: str, result: Any) -> None:
        payload = self._load()
        content = {
            "action": (action or "").strip(),
            "result": result,
        }
        payload["actions"].append(
            {
                "timestamp": self._timestamp(),
                "role": "action",
                "content": content,
            }
        )
        self._save(payload)

    def get_recent_history(self, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        payload = self._load()
        safe_limit = max(1, int(limit))
        return {
            "messages": payload["messages"][-safe_limit:],
            "actions": payload["actions"][-safe_limit:],
        }

    def clear_history(self) -> None:
        self._save({"messages": [], "actions": []})

    def _add_message(self, role: str, text: str) -> None:
        cleaned = (text or "").strip()
        if not cleaned:
            return

        payload = self._load()
        payload["messages"].append(
            {
                "timestamp": self._timestamp(),
                "role": role,
                "content": cleaned,
            }
        )
        self._save(payload)

    def _ensure_file(self) -> None:
        if self.file_path.exists():
            return
        self.file_path.write_text(
            json.dumps({"messages": [], "actions": []}, indent=2),
            encoding="utf-8",
        )

    def _load(self) -> Dict[str, List[Dict[str, Any]]]:
        self._ensure_file()
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"messages": [], "actions": []}

        messages = data.get("messages", [])
        actions = data.get("actions", [])
        if not isinstance(messages, list):
            messages = []
        if not isinstance(actions, list):
            actions = []

        return {"messages": messages, "actions": actions}

    def _save(self, payload: Dict[str, List[Dict[str, Any]]]) -> None:
        self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
