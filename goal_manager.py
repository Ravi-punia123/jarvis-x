"""Goal decomposition and dependency management for autonomous planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Goal:
    id: str
    title: str
    priority: int = 5
    retries: int = 0
    max_retries: int = 2
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    estimate_seconds: float = 1.0


class GoalManager:
    """Creates and tracks goals with dependency-aware ordering."""

    def create_goals(self, request: str) -> List[Goal]:
        text = (request or "").strip()
        if not text:
            return []

        parts = self._split_request(text)
        goals: List[Goal] = []
        for idx, part in enumerate(parts):
            goals.append(
                Goal(
                    id=f"g{idx+1}",
                    title=part,
                    priority=self._infer_priority(part),
                    dependencies=[f"g{idx}"] if idx > 0 else [],
                    estimate_seconds=self._estimate_seconds(part),
                )
            )
        return goals

    def ordered(self, goals: List[Goal]) -> List[Goal]:
        # Stable order by dependency chain, then priority.
        by_id = {goal.id: goal for goal in goals}
        visited: set[str] = set()
        output: List[Goal] = []

        def visit(goal: Goal):
            if goal.id in visited:
                return
            for dep in goal.dependencies:
                if dep in by_id:
                    visit(by_id[dep])
            visited.add(goal.id)
            output.append(goal)

        for goal in sorted(goals, key=lambda g: g.priority):
            visit(goal)
        return output

    def to_metadata(self, goals: List[Goal]) -> List[Dict[str, Any]]:
        return [
            {
                "id": g.id,
                "title": g.title,
                "priority": g.priority,
                "retries": g.retries,
                "max_retries": g.max_retries,
                "dependencies": g.dependencies,
                "status": g.status,
                "estimate_seconds": g.estimate_seconds,
            }
            for g in goals
        ]

    def _split_request(self, text: str) -> List[str]:
        lowered = text.lower()
        if " then " in lowered:
            return [part.strip() for part in text.split(" then ") if part.strip()]
        if "," in text:
            return [part.strip() for part in text.split(",") if part.strip()]
        return [text]

    def _infer_priority(self, part: str) -> int:
        lowered = part.lower()
        if any(token in lowered for token in ["urgent", "critical", "now"]):
            return 1
        if any(token in lowered for token in ["open", "launch", "start"]):
            return 2
        return 5

    def _estimate_seconds(self, part: str) -> float:
        lowered = part.lower()
        if "search" in lowered or "analyze" in lowered:
            return 3.0
        if "open" in lowered:
            return 1.5
        return 1.0
