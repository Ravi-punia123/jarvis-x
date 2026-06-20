"""VS Code workspace automation skill."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict


class VSCodeSkill:
    def run(self, command: str, **kwargs: Any) -> Dict[str, Any]:
        text = (command or "").strip()
        lowered = text.lower()

        if lowered.startswith("open folder "):
            folder = Path(text[len("open folder ") :].strip())
            return self._open_folder(folder)

        if lowered.startswith("create file "):
            path = Path(text[len("create file ") :].strip())
            content = str(kwargs.get("content", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(path.resolve()), "message": "File created"}

        if lowered.startswith("rename file ") and " to " in lowered:
            raw = text[len("rename file ") :]
            left, right = raw.split(" to ", 1)
            src = Path(left.strip())
            dst = Path(right.strip())
            src.rename(dst)
            return {"success": True, "from": str(src), "to": str(dst), "message": "File renamed"}

        if lowered.startswith("find symbol "):
            symbol = text[len("find symbol ") :].strip()
            return {"success": True, "message": f"Find symbol requested: {symbol}"}

        if lowered.startswith("replace text ") and " with " in lowered:
            payload = text[len("replace text ") :]
            target, replacement = payload.split(" with ", 1)
            return self._replace_text(target.strip(), replacement)

        if lowered.startswith("run tests"):
            return self._shell("py -3 -m unittest -q")

        if lowered.startswith("run terminal "):
            return self._shell(text[len("run terminal ") :].strip())

        if lowered.startswith("git "):
            return self._shell(text)

        return {"success": False, "error": f"Unsupported vscode command: {command}"}

    def _open_folder(self, folder: Path) -> Dict[str, Any]:
        if not folder.exists() or not folder.is_dir():
            return {"success": False, "error": "Folder not found"}
        return self._shell(f'code "{folder}"')

    def _replace_text(self, target: str, replacement: str) -> Dict[str, Any]:
        changed = 0
        for path in Path.cwd().rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            if target in content:
                path.write_text(content.replace(target, replacement), encoding="utf-8")
                changed += 1
        return {"success": True, "message": "Replace complete", "files_changed": changed}

    def _shell(self, cmd: str) -> Dict[str, Any]:
        try:
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=45)
            return {
                "success": out.returncode == 0,
                "returncode": out.returncode,
                "stdout": out.stdout[-4000:],
                "stderr": out.stderr[-4000:],
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
