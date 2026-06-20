"""YouTube automation skill."""

from __future__ import annotations

import urllib.parse
import webbrowser
from typing import Any, Dict


class YouTubeSkill:
    def run(self, command: str, **_: Any) -> Dict[str, Any]:
        text = (command or "").strip()
        lowered = text.lower()
        if lowered.startswith("search "):
            query = text[7:].strip()
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
            webbrowser.open(url, new=2)
            return {"success": True, "url": url, "message": "Opened YouTube search"}
        return {"success": False, "error": f"Unsupported youtube command: {command}"}
