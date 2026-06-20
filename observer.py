"""Background observer loop for periodic desktop state snapshots."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from memory import MemoryManager
from tool_registry import ToolRegistry
from vision import VisionManager


class Observer:
    """Continuously captures lightweight desktop context for planning."""

    def __init__(
        self,
        vision: Optional[VisionManager] = None,
        memory: Optional[MemoryManager] = None,
        registry: Optional[ToolRegistry] = None,
        interval_seconds: float = 5.0,
    ):
        self.vision = vision or VisionManager()
        self.memory = memory or MemoryManager()
        self.registry = registry or ToolRegistry()
        self.interval_seconds = max(1.0, float(interval_seconds))

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._latest_state: Dict[str, Any] = {
            "active_window": "",
            "last_screenshot": "",
            "last_analysis": {},
            "last_updated": 0.0,
        }

    def start(self) -> Dict[str, Any]:
        if self._thread and self._thread.is_alive():
            return {"success": True, "message": "Observer already running"}

        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return {"success": True, "message": "Observer started", "interval_seconds": self.interval_seconds}

    def stop(self) -> Dict[str, Any]:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        return {"success": True, "message": "Observer stopped"}

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop.is_set())

    def get_latest_state(self) -> Dict[str, Any]:
        return dict(self._latest_state)

    def _loop(self) -> None:
        while not self._stop.is_set():
            started = time.time()
            try:
                self._capture_once()
            except Exception:
                pass

            elapsed = time.time() - started
            wait_for = max(0.0, self.interval_seconds - elapsed)
            self._stop.wait(wait_for)

    def _capture_once(self) -> None:
        active_window = ""
        win_result = self.registry.execute("computer.get_active_window")
        if isinstance(win_result, dict) and win_result.get("success"):
            active_window = str(win_result.get("window", {}).get("title", ""))

        capture = self.vision.capture()
        if not capture.get("success"):
            self._latest_state = {
                "active_window": active_window,
                "last_screenshot": "",
                "last_analysis": {},
                "last_updated": time.time(),
            }
            return

        screenshot_path = capture.get("path", "")
        analysis = self.vision.analyze_image(screenshot_path, context="observer frame")
        analysis_data = analysis.get("data", {}) if isinstance(analysis, dict) and analysis.get("success") else {}

        self._latest_state = {
            "active_window": active_window,
            "last_screenshot": screenshot_path,
            "last_analysis": analysis_data,
            "last_updated": time.time(),
        }

        if active_window:
            self.memory.set_last_active_window(active_window)
            self.memory.add_window_history(active_window)

        if screenshot_path:
            self.memory.add_recent_screenshot(screenshot_path)
