"""Dynamic Multi-Agent system coordinator allocating tasks to sub-agents."""

import os
from typing import Dict, Any, List, Optional, Union
from planner import Planner
from executor import Executor
from reasoner import Reasoner
from logger import get_logger

_log = get_logger("os_coordinator")


class CoordinatorAgent:
    """Orchestrates collaborative workflows between multiple specialized sub-agents."""

    def __init__(self, planner: Planner, executor: Executor):
        self.planner = planner
        self.executor = executor
        self.reasoner = planner.reasoner
        
        # Sub-agents specifications
        self.agents = {
            "coordinator": "Decides which agents collaborate and handles overall context",
            "planner": "Splits user prompt into linear execution pipelines",
            "reasoner": "Generates structured reasoning steps",
            "vision": "Analyzes screen images and captures state",
            "memory": "Searches and summarizes facts and histories",
            "execution": "Routes commands to system tools",
            "browser": "Navigates and searches URLs",
            "coding": "Modifies codebase, commits, and formats files",
            "research": "Investigates documents and system information",
            "observer": "Continuously gathers background desktop metrics",
        }

    def coordinate(self, prompt: str, observer_state: Dict[str, Any]) -> Dict[str, Any]:
        _log.info("Coordinating execution for request: %s", prompt)
        
        # 1. Step analysis (planner acts as Planner Agent)
        self.planner.set_observer_state(observer_state)
        plan = self.planner.plan(prompt)
        
        # 2. Reasoning agent verification
        reasoning = self.reasoner.reason(prompt, observer_state)
        
        # 3. Determine agent allocation list
        allocated: List[str] = ["coordinator", "planner", "reasoner"]
        
        # Standard classification routing
        if isinstance(plan, list):
            for step in plan:
                allocated.append(self._map_step_agent(step))
        else:
            allocated.append(self._map_step_agent(plan))

        allocated = sorted(list(set(allocated)))

        # 4. Dispatch tasks
        execution_result = self.executor.execute(plan)

        return {
            "success": bool(execution_result.get("success")),
            "allocated_agents": allocated,
            "plan": plan,
            "reasoning": reasoning,
            "result": execution_result,
        }

    def _map_step_agent(self, step: Dict[str, Any]) -> str:
        action = step.get("action", "")
        module = step.get("module", "")
        
        if action == "analyze_screen" or module == "vision":
            return "vision"
        if action == "chat":
            return "reasoner"
        if module == "browser_tools" or action == "browser_request":
            return "browser"
        if action == "skill_call":
            skill = step.get("skill", "")
            if skill in {"vscode", "github", "terminal"}:
                return "coding"
            if skill == "browser":
                return "browser"
            if skill == "filesystem":
                return "execution"
        return "execution"
