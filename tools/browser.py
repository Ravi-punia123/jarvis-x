"""Browser tool module for opening URLs and performing Google searches."""

import urllib.parse
import webbrowser
from typing import Dict


def _normalize_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    if text.startswith(("http://", "https://")):
        return text
    return f"https://{text}"


def open_url(url: str = "") -> Dict[str, object]:
    """Open a URL in the default browser."""
    normalized = _normalize_url(url)
    if not normalized:
        return {"success": False, "message": "Invalid URL"}

    try:
        webbrowser.open(normalized, new=2)
        return {"success": True, "message": f"Opened {normalized}"}
    except Exception:
        return {"success": False, "message": "Failed to open URL"}


def search_google(query: str = "") -> Dict[str, object]:
    """Open a Google search in the default browser."""
    text = (query or "").strip()
    if not text:
        return {"success": False, "message": "Invalid search query"}

    encoded = urllib.parse.quote_plus(text)
    search_url = f"https://www.google.com/search?q={encoded}"
    try:
        webbrowser.open(search_url, new=2)
        return {"success": True, "message": f"Opened {search_url}"}
    except Exception:
        return {"success": False, "message": "Failed to open search results"}
