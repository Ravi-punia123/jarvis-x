"""Automation Center engine defining shutdown, backup, and routine startup recipes."""

import os
import shutil
from pathlib import Path
from typing import Dict, Any
from logger import get_logger

_log = get_logger("os_automation")


class OSAutomationCenter:
    """Orchestrates daily backup sweeps, routine configurations, and system recipe runs."""

    def __init__(self, workspace_path: str = "."):
        self.workspace = Path(workspace_path)

    def run_backup_recipe(self, dest_folder: str = "backup_vault") -> Dict[str, Any]:
        dest = Path(dest_folder)
        dest.mkdir(parents=True, exist_ok=True)
        
        copied_files = []
        # Backup only database/json config files in the project
        try:
            for item in self.workspace.glob("*.json"):
                if item.name != "chat_history.json":
                    shutil.copy2(item, dest / item.name)
                    copied_files.append(item.name)
            
            _log.info("Backup recipe successfully executed: copied %d files", len(copied_files))
            return {"success": True, "copied": copied_files, "dest": str(dest.resolve())}
        except Exception as e:
            _log.error("Backup recipe failed: %s", str(e))
            return {"success": False, "error": str(e)}
