"""Persistent memory manager for conversations and actions."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List


class MemoryManager:
    """Stores short-term, long-term, and session memory in memory.json."""

    def __init__(
        self,
        file_path: str = "memory.json",
        recent_limit: int = 40,
        long_term_limit: int = 2000,
        session_limit: int = 300,
    ):
        self.file_path = Path(file_path)
        self.recent_limit = max(10, int(recent_limit))
        self.long_term_limit = max(100, int(long_term_limit))
        self.session_limit = max(50, int(session_limit))
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
        self._cleanup_payload(payload)
        self._save(payload)

    def get_recent_history(self, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        payload = self._load()
        safe_limit = max(1, int(limit))
        return {
            "messages": payload["messages"][-safe_limit:],
            "actions": payload["actions"][-safe_limit:],
            "session": payload["session"][-safe_limit:],
        }

    def get_recent_context(self, limit: int = 20) -> List[Dict[str, Any]]:
        payload = self._load()
        safe_limit = max(1, int(limit))
        return payload["messages"][-safe_limit:]

    def get_long_term_memory(self) -> List[Dict[str, Any]]:
        payload = self._load()
        return payload["long_term"].copy()

    def add_long_term_fact(self, fact: str, tags: List[str] | None = None) -> None:
        cleaned = (fact or "").strip()
        if not cleaned:
            return
        payload = self._load()
        payload["long_term"].append(
            {
                "timestamp": self._timestamp(),
                "fact": cleaned,
                "tags": tags or [],
            }
        )
        self._cleanup_payload(payload)
        self._save(payload)

    def search_memory(self, query: str, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        payload = self._load()
        needle = (query or "").strip().lower()
        if not needle:
            return {"messages": [], "actions": [], "long_term": []}

        messages = [m for m in payload["messages"] if needle in str(m.get("content", "")).lower()]
        actions = [a for a in payload["actions"] if needle in json.dumps(a, ensure_ascii=False).lower()]
        long_term = [l for l in payload["long_term"] if needle in json.dumps(l, ensure_ascii=False).lower()]

        return {
            "messages": messages[:limit],
            "actions": actions[:limit],
            "long_term": long_term[:limit],
        }

    def summarize_memory(self, max_items: int = 12) -> str:
        payload = self._load()
        recent_messages = payload["messages"][-max_items:]
        long_facts = payload["long_term"][-max_items:]

        lines: List[str] = []
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", "")).strip().replace("\n", " ")
            if content:
                lines.append(f"[{role}] {content[:140]}")
        for fact in long_facts:
            value = str(fact.get("fact", "")).strip()
            if value:
                lines.append(f"[fact] {value[:140]}")

        if not lines:
            return "No memory yet."
        return "\n".join(lines)

    def clear_history(self) -> None:
        self._save(
            {
                "messages": [],
                "actions": [],
                "session": [],
                "long_term": [],
                "clipboard_history": [],
                "recent_tasks": [],
                "recent_clicked_elements": [],
                "window_history": [],
                "recent_screenshots": [],
                "last_active_window": "",
                "goals": [],
                "projects": [],
                "preferences": {},
                "conversation_summaries": [],
            }
        )

    def add_goal(self, title: str, status: str = "pending", priority: int = 5) -> None:
        cleaned = (title or "").strip()
        if not cleaned:
            return
        payload = self._load()
        payload["goals"].append(
            {
                "timestamp": self._timestamp(),
                "title": cleaned,
                "status": (status or "pending").strip(),
                "priority": int(priority),
            }
        )
        self._cleanup_payload(payload)
        self._save(payload)

    def add_project(self, name: str, details: str = "") -> None:
        cleaned = (name or "").strip()
        if not cleaned:
            return
        payload = self._load()
        payload["projects"].append(
            {
                "timestamp": self._timestamp(),
                "name": cleaned,
                "details": str(details or "")[:2000],
            }
        )
        self._cleanup_payload(payload)
        self._save(payload)

    def set_preference(self, key: str, value: Any) -> None:
        pref_key = (key or "").strip()
        if not pref_key:
            return
        payload = self._load()
        payload["preferences"][pref_key] = value
        self._save(payload)

    def get_preference(self, key: str, default: Any = None) -> Any:
        payload = self._load()
        return payload.get("preferences", {}).get(key, default)

    def add_conversation_summary(self, summary: str) -> None:
        cleaned = (summary or "").strip()
        if not cleaned:
            return
        payload = self._load()
        payload["conversation_summaries"].append(
            {
                "timestamp": self._timestamp(),
                "summary": cleaned[:3000],
            }
        )
        self._cleanup_payload(payload)
        self._save(payload)

    def semantic_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Lightweight token-overlap semantic search over memory sections."""
        needle = (query or "").strip().lower()
        if not needle:
            return {"success": True, "results": []}

        payload = self._load()
        query_tokens = {token for token in needle.replace("\n", " ").split() if token}

        corpus: List[Dict[str, Any]] = []
        for msg in payload["messages"]:
            corpus.append({"type": "message", "text": str(msg.get("content", "")), "item": msg})
        for fact in payload["long_term"]:
            corpus.append({"type": "long_term", "text": str(fact.get("fact", "")), "item": fact})
        for goal in payload["goals"]:
            corpus.append({"type": "goal", "text": str(goal.get("title", "")), "item": goal})
        for summary in payload["conversation_summaries"]:
            corpus.append({"type": "summary", "text": str(summary.get("summary", "")), "item": summary})

        scored: List[Dict[str, Any]] = []
        for entry in corpus:
            tokens = {token for token in entry["text"].lower().split() if token}
            if not tokens:
                continue
            overlap = len(tokens.intersection(query_tokens))
            if overlap == 0:
                continue
            score = overlap / max(1, len(query_tokens))
            scored.append({"score": round(score, 3), **entry})

        scored.sort(key=lambda item: item["score"], reverse=True)
        return {"success": True, "results": scored[: max(1, int(limit))]}

    def add_clipboard_entry(self, value: str) -> None:
        payload = self._load()
        payload["clipboard_history"].append({"timestamp": self._timestamp(), "value": str(value)[:4000]})
        self._cleanup_payload(payload)
        self._save(payload)

    def add_recent_task(self, task: str, status: str = "completed") -> None:
        payload = self._load()
        payload["recent_tasks"].append(
            {
                "timestamp": self._timestamp(),
                "task": str(task).strip(),
                "status": str(status).strip() or "completed",
            }
        )
        self._cleanup_payload(payload)
        self._save(payload)

    def add_clicked_element(self, label: str, x: int, y: int) -> None:
        payload = self._load()
        payload["recent_clicked_elements"].append(
            {
                "timestamp": self._timestamp(),
                "label": str(label).strip(),
                "x": int(x),
                "y": int(y),
            }
        )
        self._cleanup_payload(payload)
        self._save(payload)

    def add_window_history(self, title: str) -> None:
        cleaned = str(title or "").strip()
        if not cleaned:
            return
        payload = self._load()
        payload["window_history"].append({"timestamp": self._timestamp(), "title": cleaned[:300]})
        self._cleanup_payload(payload)
        self._save(payload)

    def set_last_active_window(self, title: str) -> None:
        payload = self._load()
        payload["last_active_window"] = str(title or "").strip()[:300]
        self._save(payload)

    def add_recent_screenshot(self, path: str) -> None:
        cleaned = str(path or "").strip()
        if not cleaned:
            return
        payload = self._load()
        payload["recent_screenshots"].append({"timestamp": self._timestamp(), "path": cleaned})
        self._cleanup_payload(payload)
        self._save(payload)

    def get_computer_state(self, limit: int = 20) -> Dict[str, Any]:
        payload = self._load()
        safe_limit = max(1, int(limit))
        return {
            "last_active_window": payload["last_active_window"],
            "clipboard_history": payload["clipboard_history"][-safe_limit:],
            "recent_tasks": payload["recent_tasks"][-safe_limit:],
            "recent_clicked_elements": payload["recent_clicked_elements"][-safe_limit:],
            "window_history": payload["window_history"][-safe_limit:],
            "recent_screenshots": payload["recent_screenshots"][-safe_limit:],
        }

    def _add_message(self, role: str, text: str) -> None:
        cleaned = (text or "").strip()
        if not cleaned:
            return

        payload = self._load()
        # Prevent duplicate consecutive entries with identical role and content
        if payload["messages"] and payload["messages"][-1].get("role") == role and payload["messages"][-1].get("content") == cleaned:
            return

        record = {
            "timestamp": self._timestamp(),
            "role": role,
            "content": cleaned,
        }
        payload["messages"].append(record)
        payload["session"].append(record)
        self._cleanup_payload(payload)
        self._save(payload)

    def _cleanup_payload(self, payload: Dict[str, Any]) -> None:
        payload["messages"] = payload["messages"][-self.long_term_limit:]
        payload["actions"] = payload["actions"][-self.long_term_limit:]
        payload["session"] = payload["session"][-self.session_limit:]
        payload["long_term"] = payload["long_term"][-self.long_term_limit:]
        payload["clipboard_history"] = payload["clipboard_history"][-self.long_term_limit:]
        payload["recent_tasks"] = payload["recent_tasks"][-self.long_term_limit:]
        payload["recent_clicked_elements"] = payload["recent_clicked_elements"][-self.long_term_limit:]
        payload["window_history"] = payload["window_history"][-self.long_term_limit:]
        payload["recent_screenshots"] = payload["recent_screenshots"][-self.long_term_limit:]
        payload["goals"] = payload.get("goals", [])[-self.long_term_limit:]
        payload["projects"] = payload.get("projects", [])[-self.long_term_limit:]
        payload["conversation_summaries"] = payload.get("conversation_summaries", [])[-self.long_term_limit:]
        if not isinstance(payload.get("preferences", {}), dict):
            payload["preferences"] = {}

    def _ensure_file(self) -> None:
        default_structure = {
            "messages": [],
            "actions": [],
            "session": [],
            "long_term": [],
            "clipboard_history": [],
            "recent_tasks": [],
            "recent_clicked_elements": [],
            "window_history": [],
            "recent_screenshots": [],
            "last_active_window": "",
            "goals": [],
            "projects": [],
            "preferences": {},
            "conversation_summaries": [],
        }
        if self.file_path.exists():
            try:
                # Try parsing to verify if it is valid JSON
                json.loads(self.file_path.read_text(encoding="utf-8"))
                return
            except Exception:
                # File is corrupted, we will overwrite/auto-repair it
                pass
        self._save(default_structure)

    def _load(self) -> Dict[str, Any]:
        self._ensure_file()
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        messages = data.get("messages", []) if isinstance(data.get("messages", []), list) else []
        actions = data.get("actions", []) if isinstance(data.get("actions", []), list) else []
        session = data.get("session", []) if isinstance(data.get("session", []), list) else []
        long_term = data.get("long_term", []) if isinstance(data.get("long_term", []), list) else []
        clipboard_history = data.get("clipboard_history", []) if isinstance(data.get("clipboard_history", []), list) else []
        recent_tasks = data.get("recent_tasks", []) if isinstance(data.get("recent_tasks", []), list) else []
        recent_clicked_elements = data.get("recent_clicked_elements", []) if isinstance(data.get("recent_clicked_elements", []), list) else []
        window_history = data.get("window_history", []) if isinstance(data.get("window_history", []), list) else []
        recent_screenshots = data.get("recent_screenshots", []) if isinstance(data.get("recent_screenshots", []), list) else []
        last_active_window = data.get("last_active_window", "") if isinstance(data.get("last_active_window", ""), str) else ""
        goals = data.get("goals", []) if isinstance(data.get("goals", []), list) else []
        projects = data.get("projects", []) if isinstance(data.get("projects", []), list) else []
        preferences = data.get("preferences", {}) if isinstance(data.get("preferences", {}), dict) else {}
        conversation_summaries = data.get("conversation_summaries", []) if isinstance(data.get("conversation_summaries", []), list) else []

        payload = {
            "messages": messages,
            "actions": actions,
            "session": session,
            "long_term": long_term,
            "clipboard_history": clipboard_history,
            "recent_tasks": recent_tasks,
            "recent_clicked_elements": recent_clicked_elements,
            "window_history": window_history,
            "recent_screenshots": recent_screenshots,
            "last_active_window": last_active_window,
            "goals": goals,
            "projects": projects,
            "preferences": preferences,
            "conversation_summaries": conversation_summaries,
        }
        self._cleanup_payload(payload)
        return payload

    def _save(self, payload: Dict[str, Any]) -> None:
        try:
            self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            # Prevent operations from crashing if file saving fails momentarily
            pass

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

