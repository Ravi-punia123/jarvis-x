"""Reasoning layer that transforms goals into an execution strategy."""

from __future__ import annotations

from typing import Any, Dict, List

from goal_manager import GoalManager
from logger import get_logger


class Reasoner:
    """Converts user requests to multi-goal execution intent."""

    def __init__(self):
        self.goal_manager = GoalManager()
        self.log = get_logger("reasoner")

    def reason(self, request: str, observer_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
        goals = self.goal_manager.create_goals(request)
        ordered = self.goal_manager.ordered(goals)

        strategy = {
            "intent": self._infer_intent(request),
            "observer_state": observer_state or {},
            "goals": self.goal_manager.to_metadata(ordered),
            "estimated_total_seconds": round(sum(goal.estimate_seconds for goal in ordered), 2),
            "execution_order": [goal.id for goal in ordered],
            "retry_policy": {"max_retries": max((g.max_retries for g in ordered), default=2)},
        }
        self.log.info("reasoned request='%s' goals=%s", request, len(ordered))
        return strategy

    def _infer_intent(self, request: str) -> str:
        lowered = (request or "").lower()
        if any(token in lowered for token in ["click", "type", "window", "screenshot"]):
            return "computer_use"
        if any(token in lowered for token in ["search", "browser", "google", "website"]):
            return "browser_automation"
        if any(token in lowered for token in ["file", "folder", "create", "rename"]):
            return "filesystem_automation"
        return "assistant_chat"
