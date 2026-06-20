"""Autonomous Observe->Think->Plan->Execute->Verify loop."""

from __future__ import annotations

from typing import Any, Dict, List

from logger import get_logger


class AutonomousAgentLoop:
    """Runs autonomous loop with retries and verification."""

    def __init__(self, planner, executor, observer, reasoner):
        self.planner = planner
        self.executor = executor
        self.observer = observer
        self.reasoner = reasoner
        self.log = get_logger("autonomous")

    def run(self, request: str, max_cycles: int = 3, seed_steps: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        cycle_logs: List[Dict[str, Any]] = []
        for cycle in range(1, max_cycles + 1):
            state = self.observer.get_latest_state() if self.observer else {}
            thought = self.reasoner.reason(request, state)
            if seed_steps:
                plan = list(seed_steps)
            else:
                self.planner.set_observer_state(state)
                plan = self.planner.plan(request)
            result = self.executor.execute(plan)
            verified = self._verify_result(result)

            cycle_logs.append(
                {
                    "cycle": cycle,
                    "state": state,
                    "thought": thought,
                    "plan": plan,
                    "result": result,
                    "verified": verified,
                }
            )

            if verified:
                return {"success": True, "cycles": cycle_logs, "message": "Autonomous loop completed"}
            self.log.warning("autonomous cycle=%s verify failed, retrying", cycle)

        return {"success": False, "cycles": cycle_logs, "error": "Autonomous loop exhausted retries"}

    def _verify_result(self, result: Any) -> bool:
        if isinstance(result, dict):
            if isinstance(result.get("steps"), list):
                return all(bool(step.get("success")) for step in result["steps"])
            return bool(result.get("success"))
        return bool(result)
