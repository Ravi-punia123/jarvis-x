"""Project Manager data schemas, tracking goals, status, and repositories."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from logger import get_logger

_log = get_logger("os_project_manager")


class OSProjectManager:
    """Manages active projects, milestones, task alignment, and directory details."""

    def __init__(self, storage_path: str = "projects.json"):
        self.storage_path = Path(storage_path)
        self._projects: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                self._projects = json.loads(self.storage_path.read_text(encoding="utf-8"))
            except Exception:
                self._projects = {}

    def save(self) -> None:
        try:
            self.storage_path.write_text(json.dumps(self._projects, indent=2), encoding="utf-8")
        except Exception as e:
            _log.error("Failed to save projects database: %s", str(e))

    def create_project(self, name: str, repo: str = "", goals: Optional[List[str]] = None) -> Dict[str, Any]:
        cleaned = (name or "").strip()
        if not cleaned:
            return {"success": False, "error": "Project name required"}
        
        self._projects[cleaned] = {
            "name": cleaned,
            "repository": (repo or "").strip(),
            "goals": goals or [],
            "milestones": [],
            "status": "active",
            "progress": 0.0,
        }
        self.save()
        _log.info("Created project: %s", cleaned)
        return {"success": True, "project": self._projects[cleaned]}

    def add_milestone(self, project_name: str, title: str, deadline: str = "") -> Dict[str, Any]:
        proj = self._projects.get(project_name)
        if not proj:
            return {"success": False, "error": f"Project '{project_name}' not found."}
        
        milestone = {
            "title": title.strip(),
            "deadline": deadline.strip(),
            "status": "pending",
        }
        proj["milestones"].append(milestone)
        self.save()
        return {"success": True, "milestone": milestone}

    def list_projects(self) -> List[Dict[str, Any]]:
        return list(self._projects.values())
