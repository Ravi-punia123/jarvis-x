"""Skill discovery and dispatch registry."""

from __future__ import annotations

from typing import Any, Dict

from skills.browser import BrowserSkill
from skills.email import EmailSkill
from skills.excel import ExcelSkill
from skills.filesystem import FilesystemSkill
from skills.github import GitHubSkill
from skills.terminal import TerminalSkill
from skills.vscode import VSCodeSkill
from skills.youtube import YouTubeSkill


class SkillsRegistry:
    def __init__(self):
        self.skills: Dict[str, Any] = {
            "browser": BrowserSkill(),
            "terminal": TerminalSkill(),
            "github": GitHubSkill(),
            "vscode": VSCodeSkill(),
            "excel": ExcelSkill(),
            "youtube": YouTubeSkill(),
            "email": EmailSkill(),
            "filesystem": FilesystemSkill(),
        }

    def execute(self, skill: str, command: str, **kwargs: Any) -> Dict[str, Any]:
        target = self.skills.get((skill or "").strip().lower())
        if not target:
            return {"success": False, "error": f"Unknown skill: {skill}"}
        try:
            return target.run(command, **kwargs)
        except Exception as exc:
            return {"success": False, "error": str(exc), "skill": skill, "command": command}
