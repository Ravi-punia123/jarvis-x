"""Filesystem skill wrappers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class FilesystemSkill:
    def run(self, command: str, **kwargs: Any) -> Dict[str, Any]:
        text = (command or "").strip()
        lowered = text.lower()

        if lowered.startswith("create folder "):
            path = Path(text[len("create folder ") :].strip())
            path.mkdir(parents=True, exist_ok=True)
            return {"success": True, "message": "Folder ready", "path": str(path.resolve())}

        if lowered.startswith("create file "):
            path = Path(text[len("create file ") :].strip())
            content = str(kwargs.get("content", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"success": True, "message": "File created", "path": str(path.resolve())}

        if lowered.startswith("read "):
            path = Path(text[5:].strip())
            if not path.exists() or not path.is_file():
                return {"success": False, "error": "File not found"}
            return {"success": True, "message": "File read", "path": str(path.resolve()), "content": path.read_text(encoding="utf-8")}

        if lowered.startswith("list "):
            path = Path(text[5:].strip())
            if not path.exists() or not path.is_dir():
                return {"success": False, "error": "Directory not found"}
            entries = sorted(item.name for item in path.iterdir())
            return {"success": True, "message": f"Listed {len(entries)} entries", "path": str(path.resolve()), "entries": entries}

        return {"success": False, "error": f"Unsupported filesystem command: {command}"}
