"""Persistent settings manager for JARVIS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_SETTINGS: Dict[str, Any] = {
    "llm_model": "qwen3:8b",
    "vision_model": "auto",
    "timeout_seconds": 600,
    "temperature": 0.2,
    "context_length": 8192,
    "ollama_url": "http://localhost:11434",
    "theme": "dark",
    "font_scale": 1.0,
    "voice_enabled": True,
    "microphone": "default",
    "memory_recent_limit": 40,
    "memory_long_term_limit": 2000,
    "startup_open_last_chat": True,
    "startup_auto_load_memory": True,
    "animations": True,
    "auto_speak": False,
    "mouse_speed": 1.0,
    "typing_speed": 0.02,
    "retry_count": 2,
    "safety_mode": "real",
    "vision_timeout": 600,
    "observer_interval": 5,
}


class SettingsManager:
    """Loads and persists settings as local JSON."""

    def __init__(self, file_path: str = "settings.json"):
        self.file_path = Path(file_path)
        self._settings: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            self._settings = DEFAULT_SETTINGS.copy()
            self.save()
            return

        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        merged = DEFAULT_SETTINGS.copy()
        merged.update(data)
        self._settings = merged

    def save(self) -> None:
        self.file_path.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        self._settings.update(updates)

    def all(self) -> Dict[str, Any]:
        return dict(self._settings)
