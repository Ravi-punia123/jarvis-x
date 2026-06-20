"""Terminal automation skill."""

from __future__ import annotations

import subprocess
from typing import Any, Dict


class TerminalSkill:
    def run(self, command: str, timeout: int = 30, **_: Any) -> Dict[str, Any]:
        text = (command or "").strip()
        if not text:
            return {"success": False, "error": "Terminal command is required"}
        try:
            out = subprocess.run(text, shell=True, capture_output=True, text=True, timeout=max(1, int(timeout)))
            return {
                "success": out.returncode == 0,
                "returncode": out.returncode,
                "stdout": out.stdout[-4000:],
                "stderr": out.stderr[-4000:],
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
