"""Executor layer for dispatching planned actions to tool handlers."""

import os
from typing import Dict, List, Union

from tools.browser import open_url, search_google
from tools.desktop import open_application
from tools.filesystem import (
    create_folder,
    create_text_file,
    find_file,
    list_directory,
    read_text_file,
)
from vision import VisionManager


class Executor:
    """Dispatches a planner result to the correct tool handler.

    This class keeps routing logic simple and does not contain business logic.
    """

    def __init__(self):
        self.vision = VisionManager()

    def execute(self, plan: Union[Dict[str, str], List[Dict[str, str]]]):
        if isinstance(plan, list):
            return self._execute_pipeline(plan)
        return self._execute_single(plan)

    def _execute_pipeline(self, plans: List[Dict[str, str]]):
        steps = []

        for index, step_plan in enumerate(plans, start=1):
            step_result = self._execute_single(step_plan)
            success = isinstance(step_result, dict) and bool(step_result.get("success"))
            message = self._format_step_message(step_plan, step_result)

            steps.append(
                {
                    "index": index,
                    "action": step_plan.get("action", ""),
                    "success": success,
                    "message": message,
                }
            )

            if not success:
                return {
                    "success": False,
                    "failed_step": index,
                    "failed_action": step_plan.get("action", ""),
                    "message": message,
                    "steps": steps,
                }

        return {
            "success": True,
            "message": "Pipeline completed",
            "steps": steps,
        }

    def _execute_single(self, plan: Dict[str, str]):
        action = plan.get("action")
        module = plan.get("module")

        if action == "create_folder":
            folder_path = (plan.get("path", "") or "").strip()
            if not folder_path:
                return {"success": False, "error": "Folder path is required"}
            return create_folder(folder_path)

        if action == "open_folder":
            folder_path = (plan.get("path", "") or "").strip()
            if not folder_path:
                return {"success": False, "error": "Folder path is required"}
            return self._open_folder(folder_path)

        if action == "chat":
            return self._dispatch_chat(module, plan)
        if action == "open_app":
            return self._dispatch_open_app(module, plan)
        if action == "browser_request":
            return self._dispatch_browser(module, plan)
        if action == "file_request":
            return self._dispatch_file(module, plan)
        if action == "analyze_screen":
            return self._dispatch_vision(module, plan)

        return {"success": False, "error": "Tool not implemented."}

    def _open_folder(self, path: str):
        folder_path = os.path.abspath(path)
        if not os.path.isdir(folder_path):
            return {"success": False, "error": "Folder not found"}

        try:
            os.startfile(folder_path)
            return {"success": True, "message": f"Opened {path}", "path": folder_path}
        except Exception:
            return {"success": False, "error": "Failed to open folder"}

    def _format_step_message(self, plan: Dict[str, str], result):
        action = plan.get("action", "")
        success = isinstance(result, dict) and bool(result.get("success"))

        if success:
            if action == "create_folder":
                return f"Created folder {plan.get('path', '')}".strip()
            if action == "open_folder":
                return f"Opened {plan.get('path', '')}".strip()
            if action == "browser_request":
                input_text = (plan.get("input", "") or "").strip()
                if input_text.lower().startswith("search "):
                    return f"Opened Google search for {input_text[7:].strip()}"
            return result.get("message", "Done") if isinstance(result, dict) else "Done"

        if isinstance(result, dict):
            return result.get("error") or result.get("message") or "Action failed"

        return str(result)

    def _dispatch_chat(self, module: str, plan: Dict[str, str]):
        if module != "ai":
            return "Tool not implemented."
        return f"Dispatching chat request to {module}: {plan.get('input')}"

    def _dispatch_open_app(self, module: str, plan: Dict[str, str]):
        if module != "desktop_tools":
            return "Tool not implemented."
        return open_application(plan.get("input", ""))

    def _dispatch_browser(self, module: str, plan: Dict[str, str]):
        if module != "browser_tools":
            return "Tool not implemented."

        input_text = (plan.get("input", "") or "").strip()
        lowered = input_text.lower()

        if lowered.startswith("search "):
            query = input_text[7:].strip()
            return search_google(query)

        if lowered.startswith("open "):
            target = input_text[5:].strip()
            return open_url(target)

        return open_url(input_text)

    def _dispatch_file(self, module: str, plan: Dict[str, str]):
        if module != "file_tools":
            return "Tool not implemented."

        input_text = (plan.get("input", "") or "").strip()
        lowered = input_text.lower()

        if lowered.startswith("find "):
            return find_file(input_text[5:].strip())

        if lowered.startswith("list "):
            target = input_text[5:].strip()
            return list_directory(target)

        if lowered.startswith("create folder "):
            folder_path = input_text[len("create folder ") :].strip()
            return create_folder(folder_path)

        if lowered.startswith("create file "):
            payload = input_text[len("create file ") :].strip()
            if " content " in payload.lower():
                index = payload.lower().find(" content ")
                file_path = payload[:index].strip()
                content = payload[index + len(" content ") :]
            else:
                file_path = payload
                content = ""
            return create_text_file(file_path, content)

        if lowered.startswith("read "):
            return read_text_file(input_text[5:].strip())

        return "Tool not implemented."

    def _dispatch_vision(self, module: str, plan: Dict[str, str]):
        if module != "vision":
            return {"success": False, "error": "Tool not implemented."}

        capture_result = self.vision.capture()
        if not capture_result.get("success"):
            return capture_result

        image_path = capture_result.get("path", "")
        analysis_result = self.vision.analyze(image_path)
        if not analysis_result.get("success"):
            return analysis_result

        return analysis_result
