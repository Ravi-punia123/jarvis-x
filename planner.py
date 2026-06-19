"""Request planner for routing user intents to the correct module."""

from typing import Dict, List, Optional, Union


class Planner:
    """Decides which module should handle a user request.

    This is a planning-only layer. It never executes tools or actions.
    It returns a structured action object for downstream handling.
    """

    def __init__(self):
        self.chat_keywords = [
            "what",
            "how",
            "why",
            "explain",
            "summarize",
            "tell me",
            "help",
            "write",
            "create",
            "plan",
            "analyze",
        ]
        self.open_app_keywords = [
            "open",
            "launch",
            "start",
            "run",
        ]
        self.file_keywords = [
            "file",
            "folder",
            "document",
            "read",
            "search file",
            "find file",
            "list files",
        ]
        self.browser_keywords = [
            "browser",
            "website",
            "webpage",
            "search the web",
            "open url",
            "go to",
        ]

    def plan(self, request: str) -> Union[Dict[str, str], List[Dict[str, str]]]:
        """Return one action or an ordered action list for chained requests."""
        raw_text = request.strip()
        if not raw_text:
            return {
                "action": "chat",
                "module": "ai",
                "input": request,
                "reason": "The request is a general conversation or information query.",
            }

        step_texts = self._split_pipeline(raw_text)
        if len(step_texts) > 1:
            actions: List[Dict[str, str]] = []
            last_folder: Optional[str] = None
            for step_text in step_texts:
                action = self._plan_single(step_text, last_folder)
                if action.get("action") == "create_folder" and action.get("path"):
                    last_folder = action.get("path")
                actions.append(action)
            return actions

        return self._plan_single(raw_text)

    def _plan_single(
        self,
        request: str,
        last_folder: Optional[str] = None,
    ) -> Dict[str, str]:
        text = request.strip()
        lowered = text.lower()

        if self._is_screen_analysis_request(lowered):
            return {
                "action": "analyze_screen",
                "module": "vision",
                "input": request,
                "reason": "The request asks to analyze the current screen.",
            }

        if lowered.startswith("create folder "):
            path = text[len("create folder ") :].strip()
            return {"action": "create_folder", "path": path}

        if lowered.startswith("open folder "):
            path = text[len("open folder ") :].strip()
            return {"action": "open_folder", "path": path}

        if lowered in {"open it", "open that", "open the folder"} and last_folder:
            return {"action": "open_folder", "path": last_folder}

        if lowered.startswith("search "):
            return {
                "action": "browser_request",
                "module": "browser_tools",
                "input": text,
                "reason": "The request appears to involve web browser actions.",
            }

        if lowered.startswith("open "):
            target = text[5:].strip()
            if target in {"it", "that", "the folder"} and last_folder:
                return {"action": "open_folder", "path": last_folder}
            if self._looks_like_domain_or_url(target):
                return {
                    "action": "browser_request",
                    "module": "browser_tools",
                    "input": f"open {target}",
                    "reason": "The request appears to involve web browser actions.",
                }
            return {
                "action": "open_app",
                "module": "desktop_tools",
                "input": text,
                "reason": "The request appears to require launching an application.",
            }

        if self._matches(lowered, self.file_keywords):
            return {
                "action": "file_request",
                "module": "file_tools",
                "input": request,
                "reason": "The request appears to involve file access.",
            }

        if self._is_browser_request(lowered) or self._matches(lowered, self.browser_keywords):
            return {
                "action": "browser_request",
                "module": "browser_tools",
                "input": request,
                "reason": "The request appears to involve web browser actions.",
            }

        if self._matches(lowered, self.open_app_keywords):
            return {
                "action": "open_app",
                "module": "desktop_tools",
                "input": request,
                "reason": "The request appears to require launching an application.",
            }

        return {
            "action": "chat",
            "module": "ai",
            "input": request,
            "reason": "The request is a general conversation or information query.",
        }

    def _split_pipeline(self, text: str) -> List[str]:
        lowered = text.lower()
        if " then " in lowered:
            return [part.strip() for part in text.split(" then ") if part.strip()]

        if "," in text and " and " in lowered:
            normalized = text.replace(",", " and ")
            return [part.strip() for part in normalized.split(" and ") if part.strip()]

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
        return (
            lowered.startswith("http://")
            or lowered.startswith("https://")
            or "." in lowered
        )

    def _is_screen_analysis_request(self, text: str) -> bool:
        patterns = [
            "what is on my screen",
            "what's on my screen",
            "analyze my screen",
            "analyze screen",
            "describe my screen",
        ]
        return any(pattern in text for pattern in patterns)
