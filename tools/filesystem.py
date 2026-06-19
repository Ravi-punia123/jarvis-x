"""Filesystem tool module for basic local file operations."""

from pathlib import Path
from typing import Dict


def find_file(filename: str) -> Dict[str, object]:
    """Find the first matching file under the current working directory."""
    name = (filename or "").strip()
    if not name:
        return {"success": False, "error": "Filename is required"}

    for match in Path.cwd().rglob(name):
        if match.is_file():
            resolved = str(match.resolve())
            return {
                "success": True,
                "message": f"Found {name}",
                "path": resolved,
            }

    return {"success": False, "error": "File not found"}


def list_directory(path: str) -> Dict[str, object]:
    """List entries in a directory."""
    target = Path((path or ".").strip())
    if not target.exists():
        return {"success": False, "error": "Directory not found"}
    if not target.is_dir():
        return {"success": False, "error": "Path is not a directory"}

    entries = sorted(item.name for item in target.iterdir())
    return {
        "success": True,
        "message": f"Listed {len(entries)} entries",
        "path": str(target.resolve()),
        "entries": entries,
    }


def create_folder(path: str) -> Dict[str, object]:
    """Create a folder, including parent folders when needed."""
    target = Path((path or "").strip())
    if not str(target):
        return {"success": False, "error": "Folder path is required"}

    target.mkdir(parents=True, exist_ok=True)
    return {
        "success": True,
        "message": "Folder ready",
        "path": str(target.resolve()),
    }


def create_text_file(path: str, content: str = "") -> Dict[str, object]:
    """Create or overwrite a text file."""
    target = Path((path or "").strip())
    if not str(target):
        return {"success": False, "error": "File path is required"}

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "message": "File created",
        "path": str(target.resolve()),
    }


def read_text_file(path: str) -> Dict[str, object]:
    """Read a text file as UTF-8."""
    target = Path((path or "").strip())
    if not target.exists() or not target.is_file():
        return {"success": False, "error": "File not found"}

    content = target.read_text(encoding="utf-8")
    return {
        "success": True,
        "message": "File read",
        "path": str(target.resolve()),
        "content": content,
    }
