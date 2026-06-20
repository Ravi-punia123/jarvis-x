"""Learning Engine keeping lightweight priority records of user preference statistics."""

import json
from pathlib import Path
from typing import Dict, Any, List
from logger import get_logger

_log = get_logger("os_learning")


class OSLearningEngine:
    """Tracks preferred workflows, frequent skills, and execution actions stats."""

    def __init__(self, data_path: str = "learning_stats.json"):
        self.data_path = Path(data_path)
        self.stats: Dict[str, Any] = {
            "workflow_frequency": {},
            "skill_frequency": {},
            "successful_actions": 0,
            "failed_actions": 0,
        }
        self._load()

    def _load(self) -> None:
        if self.data_path.exists():
            try:
                self.stats = json.loads(self.data_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def save(self) -> None:
        try:
            self.data_path.write_text(json.dumps(self.stats, indent=2), encoding="utf-8")
        except Exception as e:
            _log.error("Failed to save learning logs: %s", str(e))

    def record_action(self, action_type: str, success: bool) -> None:
        if success:
            self.stats["successful_actions"] = self.stats.get("successful_actions", 0) + 1
        else:
            self.stats["failed_actions"] = self.stats.get("failed_actions", 0) + 1
        self.save()

    def record_skill_usage(self, skill: str) -> None:
        freq = self.stats.setdefault("skill_frequency", {})
        freq[skill] = freq.get(skill, 0) + 1
        self.save()
