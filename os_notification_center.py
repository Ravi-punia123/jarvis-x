"""Event router and proactive notification manager for system states."""

import time
from typing import Dict, Any, List, Callable, Optional
from logger import get_logger

_log = get_logger("os_notification")


class OSNotificationCenter:
    """Proactively delivers smart desktop alerts and monitors background system states."""

    def __init__(self):
        self._listeners: List[Callable[[str, Dict[str, Any]], None]] = []
        self._notifications_log: List[Dict[str, Any]] = []

    def register_listener(self, listener: Callable[[str, Dict[str, Any]], None]) -> None:
        self._listeners.append(listener)

    def notify(self, title: str, message: str, level: str = "info") -> None:
        alert = {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": time.time(),
        }
        self._notifications_log.append(alert)
        _log.info("Notification triggered: [%s] %s - %s", level, title, message)
        
        for listener in self._listeners:
            try:
                listener("notification", alert)
            except Exception:
                pass

    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._notifications_log[-limit:]
