"""Request planner for routing user intents to modules and computer actions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from goal_manager import GoalManager
from logger import get_logger
from reasoner import Reasoner


class Planner:
    """Decides which module should handle a user request and builds pipelines."""

    def __init__(self):
        self.open_app_keywords = ["open", "launch", "start", "run"]
        self.file_keywords = ["file", "folder", "document", "read", "find file", "list files"]
        self.browser_keywords = ["browser", "website", "webpage", "search the web", "open url", "go to"]
        self.computer_keywords = [
            "click",
            "double click",
            "right click",
            "scroll",
            "type",
            "press",
            "hotkey",
            "copy",
            "paste",
            "clipboard",
            "switch window",
            "activate window",
            "close",
            "screenshot",
        ]
        self.observer_state: Dict[str, Any] = {}
        self.goal_manager = GoalManager()
        self.reasoner = Reasoner()
        self.log = get_logger("planner")

    def set_observer_state(self, state: Dict[str, Any]) -> None:
        self.observer_state = dict(state or {})

    def plan(self, request: str) -> Union[Dict[str, str], List[Dict[str, str]]]:
        """Return one action or an ordered action list for chained requests."""
        raw_text = request.strip()
        if not raw_text:
            return self._chat_plan(request)
        self.log.info("planning request='%s'", raw_text)

        reasoning = self.reasoner.reason(raw_text, self.observer_state)
        goals = self.goal_manager.ordered(self.goal_manager.create_goals(raw_text))

        if self._is_autonomous_workflow(raw_text.lower()):
            pipeline = self._build_autonomous_pipeline(raw_text)
            pipeline["reasoning"] = reasoning
            pipeline["goals"] = self.goal_manager.to_metadata(goals)
            return pipeline

        step_texts = self._split_pipeline(raw_text)
        if len(step_texts) > 1:
            actions: List[Dict[str, str]] = []
            last_folder: Optional[str] = None
            for idx, step_text in enumerate(step_texts):
                action = self._plan_single(step_text, last_folder)
                action["goal_id"] = goals[idx].id if idx < len(goals) else f"g{idx+1}"
                action["priority"] = goals[idx].priority if idx < len(goals) else 5
                if action.get("action") == "create_folder" and action.get("path"):
                    last_folder = action.get("path")
                actions.append(action)
            return actions

        single = self._plan_single(raw_text)
        if goals:
            single["goal_id"] = goals[0].id
            single["priority"] = goals[0].priority
            single["estimated_order"] = 1
        single["reasoning"] = reasoning
        return single

    def _plan_single(self, request: str, last_folder: Optional[str] = None) -> Dict[str, str]:
        text = request.strip()
        lowered = text.lower()
        intent = self._detect_intent(lowered)

        # 1. Vision & Screen Analysis
        if self._is_screen_analysis_request(lowered) or "analyze" in lowered or "screenshot" in lowered:
            if "take screenshot" in lowered or lowered == "screenshot":
                return {
                    "action": "take_screenshot",
                    "module": "computer_tools",
                    "input": text,
                    "intent": "computer_use",
                    "reason": "Capture the current desktop screen.",
                }
            return {
                "action": "analyze_screen",
                "module": "vision",
                "input": request,
                "intent": "screenshot_analysis",
                "reason": "Analyze or describe the current screen state.",
            }

        # 2. File & Folder Operations
        if lowered.startswith("create folder "):
            return {"action": "create_folder", "path": text[len("create folder ") :].strip(), "module": "file_tools", "intent": "file_analysis"}

        if lowered.startswith("open folder "):
            return {"action": "open_folder", "path": text[len("open folder ") :].strip(), "module": "file_tools", "intent": "file_analysis"}

        if lowered in {"open it", "open that", "open the folder"} and last_folder:
            return {"action": "open_folder", "path": last_folder, "module": "file_tools", "intent": "file_analysis"}

        # 3. Developer Workflow (Git & VS Code)
        if lowered.startswith("git ") or "github" in lowered or "commit" in lowered or "push" in lowered or "pull" in lowered:
            return self._skill_plan("github", request, "developer_workflow")

        if "vscode" in lowered or "vs code" in lowered or lowered.startswith("find symbol "):
            return self._skill_plan("vscode", request, "editor_automation")

        # 4. Applications & Commands execution
        if lowered.startswith("run ") or lowered.startswith("terminal ") or lowered.startswith("execute ") or lowered.startswith("cmd "):
            clean_cmd = text
            for prefix in ["run ", "terminal ", "execute ", "cmd "]:
                if lowered.startswith(prefix):
                    clean_cmd = text[len(prefix):].strip()
                    break
            return self._skill_plan("terminal", clean_cmd, "terminal_automation")

        # 5. Media & Utilities
        if "youtube" in lowered:
            return self._skill_plan("youtube", request, "media_automation")

        if lowered.startswith("email") or lowered.startswith("compose") or "mail" in lowered:
            return self._skill_plan("email", request, "email_automation")

        if "excel" in lowered or "spreadsheet" in lowered or "csv" in lowered:
            return self._skill_plan("excel", request, "spreadsheet_automation")

        # 6. Web & Browser
        if lowered.startswith("search ") or "google" in lowered or self._is_browser_request(lowered) or self._matches(lowered, self.browser_keywords):
            return self._skill_plan("browser", request, "browser_request")

        # 7. Core Computer control actions
        computer_action = self._plan_computer_action(text)
        if computer_action:
            return computer_action

        # 8. File system generic keywords
        if self._matches(lowered, self.file_keywords) or "find" in lowered or "delete" in lowered or "rename" in lowered or "move" in lowered or "copy" in lowered or "paste" in lowered:
            skill_plan = self._skill_plan("filesystem", request, "file_analysis")
            if skill_plan:
                return skill_plan
            return {
                "action": "file_request",
                "module": "file_tools",
                "input": request,
                "intent": "file_analysis",
                "reason": "Read, create, or modify filesystem elements.",
            }

        if self._matches(lowered, self.open_app_keywords) or "launch" in lowered:
            return {
                "action": "open_app",
                "module": "desktop_tools",
                "input": request,
                "intent": "desktop_automation",
                "reason": "Launch specified application from desktop.",
            }

        return self._chat_plan(request, intent)

    def _skill_plan(self, skill: str, command: str, intent: str) -> Dict[str, str]:
        return {
            "action": "skill_call",
            "module": "skills",
            "skill": skill,
            "input": command,
            "intent": intent,
            "reason": f"The request is delegated to the {skill} skill.",
        }

    def _plan_computer_action(self, text: str) -> Optional[Dict[str, str]]:
        lowered = text.lower().strip()

        if lowered.startswith("take screenshot") or lowered == "screenshot":
            return {
                "action": "take_screenshot",
                "module": "computer_tools",
                "input": text,
                "intent": "computer_use",
                "reason": "The request asks to capture the current screen.",
            }

        if lowered.startswith("read clipboard"):
            return {
                "action": "paste",
                "module": "computer_tools",
                "input": "read clipboard",
                "intent": "computer_use",
                "reason": "The request asks to inspect clipboard content.",
            }

        if self._matches(lowered, self.computer_keywords):
            action = "computer_request"
            for name in ["double_click", "right_click", "click", "type", "press", "hotkey", "scroll", "drag", "move_mouse", "copy", "paste", "activate_window"]:
                if name.replace("_", " ") in lowered:
                    action = name
                    break

            if lowered.startswith("copy"):
                action = "copy"
            elif lowered.startswith("paste"):
                action = "paste"
            elif lowered.startswith("switch window") or lowered.startswith("activate window"):
                action = "activate_window"

            return {
                "action": action,
                "module": "computer_tools",
                "input": text,
                "intent": "computer_use",
                "reason": "The request appears to require desktop computer control.",
            }

        return None

    def _build_autonomous_pipeline(self, request: str) -> Dict[str, Any]:
        text = request.strip()
        lowered = text.lower()
        steps: List[Dict[str, Any]] = []

        if "open chrome" in lowered:
            steps.append({"action": "open_app", "module": "desktop_tools", "input": "open chrome"})
            steps.append({"action": "wait", "module": "computer_tools", "seconds": 1.5})

        if "search " in lowered:
            query = text[text.lower().find("search ") + len("search ") :].strip()
            if "," in query:
                query = query.split(",", 1)[0].strip()
            steps.extend(
                [
                    {
                        "action": "ground_and_click",
                        "module": "computer_tools",
                        "target": "address bar",
                        "reason": "Focus browser address/search bar",
                    },
                    {"action": "type", "module": "computer_tools", "input": query},
                    {"action": "press", "module": "computer_tools", "input": "enter"},
                    {"action": "wait", "module": "computer_tools", "seconds": 2.0},
                ]
            )

        if "first result" in lowered:
            steps.append(
                {
                    "action": "ground_and_click",
                    "module": "computer_tools",
                    "target": "first result",
                    "reason": "Open first search result",
                }
            )

        if "scroll down" in lowered:
            steps.append({"action": "scroll", "module": "computer_tools", "input": "scroll down"})

        if "switch window" in lowered:
            steps.append({"action": "hotkey", "module": "computer_tools", "input": "alt tab"})

        if "copy" in lowered:
            steps.append({"action": "copy", "module": "computer_tools", "input": "copy"})

        if "paste" in lowered:
            steps.append({"action": "paste", "module": "computer_tools", "input": "paste"})

        if "close chrome" in lowered:
            steps.append({"action": "activate_window", "module": "computer_tools", "input": "activate window chrome"})
            steps.append({"action": "hotkey", "module": "computer_tools", "input": "hotkey alt f4"})

        if "take screenshot" in lowered:
            steps.append({"action": "take_screenshot", "module": "computer_tools", "input": "take screenshot"})

        if not steps:
            return self._plan_single(request)

        return {
            "action": "autonomous_loop",
            "module": "agent_brain",
            "intent": "autonomous_computer_workflow",
            "input": request,
            "steps": steps,
            "reason": "Generated autonomous Observe-Think-Plan-Execute-Verify workflow.",
        }

    def _chat_plan(self, request: str, intent: str = "chat") -> Dict[str, str]:
        return {
            "action": "chat",
            "module": "ai",
            "input": request,
            "intent": intent,
            "reason": "The request is a general conversation or information query.",
        }

    def _detect_intent(self, lowered: str) -> str:
        if any(word in lowered for word in ["click", "scroll", "hotkey", "clipboard", "window", "screenshot"]):
            return "computer_use"
        if any(word in lowered for word in ["code", "python", "javascript", "debug", "stack trace", "function", "class"]):
            return "coding_request"
        if any(word in lowered for word in ["image", "photo", "picture", "diagram", "ocr", "screen"]):
            return "image_analysis"
        if any(word in lowered for word in ["file", "folder", "pdf", "docx", "csv", "xlsx", "json", ".py", ".js"]):
            return "file_analysis"
        if any(word in lowered for word in ["open app", "launch", "desktop", "automation", "notepad", "calculator"]):
            return "desktop_automation"
        if any(word in lowered for word in ["search", "google", "browser", "url", "website", "http"]):
            return "browser_request"
        return "chat"

    def _split_pipeline(self, text: str) -> List[str]:
        lowered = text.lower()
        if " then " in lowered:
            return [part.strip() for part in text.split(" then ") if part.strip()]

        if "," in text:
            parts = [part.strip() for part in text.split(",") if part.strip()]
            if len(parts) > 1:
                return parts

        return [text]

    def _matches(self, text: str, keywords: List[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _is_browser_request(self, text: str) -> bool:
        if text.startswith("search "):
            return True
        if text.startswith("open http://") or text.startswith("open https://"):
            return True
        if text.startswith("open "):
            target = text[5:].strip()
            if "." in target:
                return True
        return False

    def _looks_like_domain_or_url(self, target: str) -> bool:
        lowered = target.lower()
        return lowered.startswith("http://") or lowered.startswith("https://") or "." in lowered

    def _is_screen_analysis_request(self, text: str) -> bool:
        patterns = [
            "what is on my screen",
            "what's on my screen",
            "analyze my screen",
            "analyze screen",
            "describe my screen",
        ]
        return any(pattern in text for pattern in patterns)

    def _is_autonomous_workflow(self, lowered: str) -> bool:
        has_sequence = " then " in lowered or lowered.count(",") >= 2
        computer_context = any(
            token in lowered
            for token in [
                "open chrome",
                "first result",
                "switch window",
                "copy selected text",
                "paste into",
                "click",
                "scroll",
                "hotkey",
            ]
        )
        if has_sequence and computer_context:
            return True
        key_patterns = [
            "open chrome",
            "first result",
            "switch window",
            "copy selected text",
            "paste into",
        ]
        return any(pattern in lowered for pattern in key_patterns)
