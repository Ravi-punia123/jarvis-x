"""Workflow engine parser and runner for sequential routine execution."""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from executor import Executor
from logger import get_logger

_log = get_logger("workflow_engine")


class WorkflowEngine:
    """Manages creation, parsing, saving, and executing automated task routines."""

    def __init__(self, executor: Executor, save_path: str = "workflows.json"):
        self.executor = executor
        self.save_path = Path(save_path)
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.save_path.exists():
            default = {
                "morning_routine": [
                    {"action": "skill_call", "skill": "vscode", "input": "open folder C:/Users/ravip/Desktop/jarvis"},
                    {"action": "wait", "seconds": 2.0},
                    {"action": "skill_call", "skill": "browser", "input": "open https://github.com"}
                ]
            }
            self.save_workflow("morning_routine", default["morning_routine"])

    def load_workflows(self) -> Dict[str, List[Dict[str, Any]]]:
        try:
            return json.loads(self.save_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_workflow(self, name: str, steps: List[Dict[str, Any]]) -> None:
        workflows = self.load_workflows()
        workflows[name] = steps
        try:
            self.save_path.write_text(json.dumps(workflows, indent=2), encoding="utf-8")
        except Exception as e:
            _log.error("Failed to write workflow config: %s", str(e))

    def run_workflow(self, name: str) -> Dict[str, Any]:
        workflows = self.load_workflows()
        steps = workflows.get(name)
        if not steps:
            return {"success": False, "error": f"Workflow '{name}' not found."}

        _log.info("Running workflow %s with %d steps", name, len(steps))
        # Direct piping into the executor pipeline execution
        result = self.executor.execute(steps)
        return {"success": bool(result.get("success")), "result": result, "workflow": name}
