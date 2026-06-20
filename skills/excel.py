"""Excel automation skill (stub with structured responses)."""

from __future__ import annotations

from typing import Any, Dict


class ExcelSkill:
    def run(self, command: str, **_: Any) -> Dict[str, Any]:
        return {"success": True, "message": f"Excel skill accepted command: {command}"}
