"""Browser automation skill."""

from __future__ import annotations

import urllib.parse
import webbrowser
from typing import Any, Dict


class BrowserSkill:
    def run(self, command: str, **kwargs: Any) -> Dict[str, Any]:
        text = (command or "").strip()
        lowered = text.lower()

        if lowered.startswith("open "):
            url = text[5:].strip()
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            return self._open(url)

        if lowered.startswith("search "):
            query = text[7:].strip()
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
            return self._open(url)

        if lowered.startswith("close tab"):
            return {"success": True, "message": "Close tab requested"}
        if lowered.startswith("switch tab"):
            return {"success": True, "message": "Switch tab requested"}
        if lowered.startswith("read webpage"):
            return {"success": True, "message": "Read webpage requested"}
        if lowered.startswith("summarize"):
            return {"success": True, "message": "Summarize webpage requested"}
        if lowered.startswith("download"):
            return {"success": True, "message": "Download requested"}

        return {"success": False, "error": f"Unsupported browser command: {command}"}

    def _open(self, url: str) -> Dict[str, Any]:
        try:
            webbrowser.open(url, new=2)
            return {"success": True, "message": f"Opened {url}", "url": url}
        except Exception as exc:
            return {"success": False, "error": str(exc), "url": url}
