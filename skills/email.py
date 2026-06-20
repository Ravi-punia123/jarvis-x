"""Email automation skill."""

from __future__ import annotations

import urllib.parse
import webbrowser
from typing import Any, Dict


class EmailSkill:
    def run(self, command: str, to: str = "", subject: str = "", body: str = "", **_: Any) -> Dict[str, Any]:
        text = (command or "").strip().lower()
        if text.startswith("compose"):
            mailto = f"mailto:{to}?subject={urllib.parse.quote_plus(subject)}&body={urllib.parse.quote_plus(body)}"
            webbrowser.open(mailto, new=1)
            return {"success": True, "message": "Opened mail composer", "mailto": mailto}
        return {"success": False, "error": f"Unsupported email command: {command}"}
