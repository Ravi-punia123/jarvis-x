"""GitHub/Git workflow skill."""

from __future__ import annotations

import subprocess
from typing import Any, Dict


class GitHubSkill:
    def run(self, command: str, **_: Any) -> Dict[str, Any]:
        text = (command or "").strip().lower()
        if text in {"git status", "status"}:
            return self._git("git status --short --branch")
        if text.startswith("git "):
            return self._git(text)
        return {"success": False, "error": f"Unsupported github command: {command}"}

    def _git(self, cmd: str) -> Dict[str, Any]:
        try:
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return {
                "success": out.returncode == 0,
                "returncode": out.returncode,
                "stdout": out.stdout[-4000:],
                "stderr": out.stderr[-4000:],
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
