"""Desktop tool module for opening common Windows applications."""

import os
import shutil
from typing import Dict, List

APP_ALIASES = {
    "notepad": ["notepad.exe", "notepad"],
    "calculator": ["calc.exe", "calculator"],
    "paint": ["mspaint.exe", "paint"],
    "cmd": ["cmd.exe", "cmd"],
    "vscode": ["code.cmd", "Code.exe", "code", "vscode"],
    "chrome": ["chrome.exe", "chrome", "google-chrome", "google-chrome.exe"],
}

DISPLAY_NAMES = {
    "notepad": "Notepad",
    "calculator": "Calculator",
    "paint": "Paint",
    "cmd": "Command Prompt",
    "vscode": "VS Code",
    "chrome": "Chrome",
}


def _extract_app_name(request: str) -> str:
    text = (request or "").strip().lower()
    cleaned = text.replace("open ", "").replace("launch ", "").replace("start ", "")

    for alias in APP_ALIASES:
        if alias in cleaned:
            return alias

    for word in cleaned.split():
        if word in APP_ALIASES:
            return word

    return cleaned


def _resolve_executable(app_name: str) -> str:
    candidates: List[str] = APP_ALIASES.get(app_name, [app_name])
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        if os.path.exists(candidate):
            return candidate
    return ""


def open_application(app_name: str = "") -> Dict[str, object]:
    """Open a known Windows application if it is available."""
    normalized = _extract_app_name(app_name)
    if not normalized:
        return {"success": False, "message": "Application not found"}

    executable = _resolve_executable(normalized)
    if not executable:
        return {"success": False, "message": "Application not found"}

    try:
        os.startfile(executable)
        label = DISPLAY_NAMES.get(normalized, normalized.title())
        return {"success": True, "message": f"Opened {label}"}
    except Exception:
        return {"success": False, "message": "Application not found"}
