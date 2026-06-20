"""Security Center managing user approval thresholds and audit logging logs."""

import time
import json
from pathlib import Path
from typing import Dict, Any, List
from logger import get_logger

_log = get_logger("os_security")


class OSSecurityCenter:
    """Evaluates commands for security risk and manages user approval audit trails."""

    def __init__(self, audit_log_path: str = "audit_log.json"):
        self.audit_log_path = Path(audit_log_path)
        self._audit_trail: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.audit_log_path.exists():
            try:
                self._audit_trail = json.loads(self.audit_log_path.read_text(encoding="utf-8"))
            except Exception:
                self._audit_trail = []

    def save(self) -> None:
        try:
            self.audit_log_path.write_text(json.dumps(self._audit_trail, indent=2), encoding="utf-8")
        except Exception as e:
            _log.error("Failed to write security logs: %s", str(e))

    def evaluate_risk(self, command: str) -> bool:
        """Return True if command performs high-risk operations requiring approval."""
        lowered = str(command or "").lower().strip()
        risk_keywords = ["rmdir", "delete", "rm -rf", "format", "shutdown", "reboot"]
        return any(keyword in lowered for keyword in risk_keywords)

    def log_approval(self, command: str, approved: bool, user: str = "user") -> None:
        record = {
            "timestamp": time.time(),
            "command": command,
            "approved": approved,
            "user": user,
        }
        self._audit_trail.append(record)
        self.save()
        _log.info("Audit log written: Command='%s' Approved=%s", command, approved)
