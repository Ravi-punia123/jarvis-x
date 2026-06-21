"""Executor layer for dispatching planned actions to tool handlers."""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union

from autonomous_agent import AutonomousAgentLoop
from logger import get_logger
from memory import MemoryManager
from observer import Observer
from screen_grounding import ScreenGrounder
from settings_manager import SettingsManager
from skills_registry import SkillsRegistry
from tool_registry import ToolRegistry
from vision import VisionManager
from reasoner import Reasoner


class Executor:
    """Dispatches a planner result to the correct tool handler.

    This class keeps routing logic simple and does not contain business logic.
    """

    def __init__(self):
        self.vision = VisionManager()
        self.registry = ToolRegistry()
        self.skills = SkillsRegistry()
        self.memory = MemoryManager()
        self.settings = SettingsManager()
        self.grounder = ScreenGrounder(self.vision)
        self.observer = Observer(self.vision, self.memory, self.registry, self.settings.get("observer_interval", 5))
        self.reasoner = Reasoner()
        self.autonomous_loop = AutonomousAgentLoop(None, self, self.observer, self.reasoner)
        self.log = get_logger("executor")

        self.safety_mode = str(self.settings.get("safety_mode", "real"))
        self.confirmation_mode = self.safety_mode == "confirm"
        self.dry_run_mode = self.safety_mode == "dry_run"
        self.max_retries = int(self.settings.get("retry_count", 2))
        self.timeout_seconds = int(self.settings.get("vision_timeout", 600))

        self._cancel_requested = False
        self._emergency_stop = False

    def execute(self, plan: Union[Dict[str, str], List[Dict[str, str]]]):
        if self._emergency_stop:
            return {"success": False, "error": "Emergency stop active"}

        if isinstance(plan, list):
            return self._execute_pipeline(plan)
        return self._execute_single(plan)

    def stream_execute(self, plan: Union[Dict[str, Any], List[Dict[str, Any]]]):
        """Yield incremental execution events for UI streaming."""
        yield {"event": "thinking", "message": "Thinking..."}
        yield {"event": "planning", "message": "Planning"}

        if isinstance(plan, list):
            for idx, step in enumerate(plan, start=1):
                action = step.get("action", "step")
                yield {"event": "step_start", "step": idx, "action": action, "message": f"Executing {action}"}
                result = self._execute_single(step)
                success = isinstance(result, dict) and bool(result.get("success"))
                yield {
                    "event": "step_result",
                    "step": idx,
                    "action": action,
                    "success": success,
                    "result": result,
                    "message": result.get("message") if isinstance(result, dict) else str(result),
                }
                if not success:
                    yield {"event": "finished", "success": False, "message": "Execution failed"}
                    return
            yield {"event": "finished", "success": True, "message": "Finished"}
            return

        action = plan.get("action", "task") if isinstance(plan, dict) else "task"
        yield {"event": "step_start", "step": 1, "action": action, "message": f"Executing {action}"}
        result = self.execute(plan)
        success = isinstance(result, dict) and bool(result.get("success"))
        yield {"event": "step_result", "step": 1, "action": action, "success": success, "result": result, "message": result.get("message", "Done") if isinstance(result, dict) else str(result)}
        yield {"event": "finished", "success": success, "message": "Finished" if success else "Execution failed"}

    def set_mode(self, mode: str) -> Dict[str, Any]:
        normalized = str(mode or "").strip().lower()
        if normalized not in {"dry_run", "confirm", "real"}:
            return {"success": False, "error": "Mode must be dry_run, confirm, or real"}
        self.safety_mode = normalized
        self.dry_run_mode = normalized == "dry_run"
        self.confirmation_mode = normalized == "confirm"
        return {"success": True, "mode": normalized}

    def request_cancel(self) -> Dict[str, Any]:
        self._cancel_requested = True
        return {"success": True, "message": "Cancel requested"}

    def emergency_stop(self) -> Dict[str, Any]:
        self._emergency_stop = True
        self._cancel_requested = True
        return {"success": True, "message": "Emergency stop activated"}

    def clear_emergency_stop(self) -> Dict[str, Any]:
        self._emergency_stop = False
        self._cancel_requested = False
        return {"success": True, "message": "Emergency stop cleared"}

    def _execute_pipeline(self, plans: List[Dict[str, str]]):
        steps = []

        for index, step_plan in enumerate(plans, start=1):
            if self._cancel_requested:
                return {
                    "success": False,
                    "failed_step": index,
                    "failed_action": step_plan.get("action", ""),
                    "message": "Execution cancelled",
                    "steps": steps,
                }

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
        skill = plan.get("skill")
        input_text = plan.get("input", "")

        if self._emergency_stop:
            return {"success": False, "error": "Emergency stop active"}

        # 1. Verification checker
        def _verify_action() -> bool:
            try:
                # If we created a file, check if it exists
                if action == "create_file" or (action == "skill_call" and "create file" in str(input_text).lower()):
                    import re
                    match = re.search(r"create file\s+(.+)", str(input_text), re.IGNORECASE)
                    if match:
                        file_path = os.path.abspath(match.group(1).strip())
                        return os.path.isfile(file_path)

                # If we created a folder, check if it exists
                if action == "create_folder" or (action == "skill_call" and "create folder" in str(input_text).lower()):
                    path_val = plan.get("path")
                    if not path_val and "create folder" in str(input_text).lower():
                        import re
                        match = re.search(r"create folder\s+(.+)", str(input_text), re.IGNORECASE)
                        if match:
                            path_val = match.group(1).strip()
                    if path_val:
                        return os.path.isdir(os.path.abspath(path_val))
            except Exception:
                pass
            return True

        # 2. Re-prioritized runner that attempts native skills registry first
        def _dispatch_execution():
            if action == "create_folder":
                folder_path = (plan.get("path", "") or "").strip()
                if not folder_path:
                    return {"success": False, "error": "Folder path is required"}
                res = self.skills.execute("filesystem", f"create folder {folder_path}")
                if res.get("success"):
                    return res
                return self.registry.route_and_execute("create_folder", path=folder_path)

            if action == "open_folder":
                folder_path = (plan.get("path", "") or "").strip()
                if not folder_path:
                    return {"success": False, "error": "Folder path is required"}
                return self._open_folder(folder_path)

            if action == "wait":
                seconds = float(plan.get("seconds", 1.0))
                return self._wait(seconds)

            if action == "ground_and_click":
                target = str(plan.get("target", "")).strip()
                return self._ground_and_click(target)

            if action == "computer_pipeline":
                return self._execute_pipeline(plan.get("steps", []))

            if action == "autonomous_loop":
                request = str(plan.get("input", "")).strip()
                if not request:
                    return {"success": False, "error": "Autonomous loop request is required"}
                self.autonomous_loop.planner = plan.get("planner_ref") or self.autonomous_loop.planner
                seed_steps = plan.get("steps") if isinstance(plan.get("steps"), list) else None
                return self.autonomous_loop.run(request, max_cycles=3, seed_steps=seed_steps)

            if action == "switch_model":
                target_model = plan.get("arguments", {}).get("model", "")
                if not target_model:
                    target_model = plan.get("model", "")
                res = self._switch_model(target_model)
                res["action"] = "switch_model"
                return res

            if action == "chat":
                return self._dispatch_chat(module, plan)
            if action == "skill_call":
                return self._dispatch_skill(module, plan)
            if action == "open_app":
                return self._dispatch_open_app(module, plan)
            if action == "browser_request":
                return self._dispatch_browser(module, plan)
            if action == "file_request":
                return self._dispatch_file(module, plan)
            if action == "analyze_screen":
                return self._dispatch_vision(module, plan)
            if action in {
                "click",
                "double_click",
                "right_click",
                "type",
                "press",
                "hotkey",
                "scroll",
                "drag",
                "move_mouse",
                "copy",
                "paste",
                "activate_window",
                "take_screenshot",
                "computer_request",
            }:
                return self._dispatch_computer(module, plan)

            return {"success": False, "error": "Tool not implemented."}

        # 3. Try execution loop with verification and up to 2 retries
        attempt = 0
        last_res = {"success": False, "error": "Not executed"}
        while attempt <= self.max_retries:
            attempt += 1
            if self._cancel_requested or self._emergency_stop:
                return {"success": False, "error": "Execution cancelled"}

            # Safely invoke via _dispatch_execution (under self._run_with_timeout or similar if needed,
            # but since self._run_with_safety is the designated wrapper, we use it directly on the inner lambda).
            last_res = self._run_with_safety(_dispatch_execution, action or "execute_single")

            # Check verification
            if isinstance(last_res, dict) and last_res.get("success"):
                if _verify_action():
                    last_res["verified"] = True
                    return last_res
                else:
                    self.log.warning("Verification failed for action=%s, attempt=%s", action, attempt)
                    last_res = {"success": False, "error": "Verification check failed", "verified": False}

            if attempt <= self.max_retries:
                self.log.info("Retrying failed action=%s, attempt=%s", action, attempt)
                time.sleep(0.2)

        return last_res

    def _dispatch_skill(self, module: str, plan: Dict[str, Any]):
        if module != "skills":
            return {"success": False, "error": "Skill module mismatch"}
        skill = str(plan.get("skill", "")).strip().lower()
        command = str(plan.get("input", ""))
        return self._run_with_safety(lambda: self.skills.execute(skill, command), "skill_call")

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
        return self._run_with_safety(lambda: self.registry.route_and_execute("open_app", input_text=plan.get("input", "")), "open_app")

    def _dispatch_browser(self, module: str, plan: Dict[str, str]):
        if module != "browser_tools":
            return "Tool not implemented."
        return self._run_with_safety(lambda: self.registry.route_and_execute("browser_request", input_text=plan.get("input", "")), "browser_request")

    def _dispatch_file(self, module: str, plan: Dict[str, str]):
        if module != "file_tools":
            return "Tool not implemented."
        return self._run_with_safety(lambda: self.registry.route_and_execute("file_request", input_text=plan.get("input", "")), "file_request")

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

    def _dispatch_computer(self, module: str, plan: Dict[str, str]):
        if module != "computer_tools":
            return {"success": False, "error": "Tool not implemented."}

        action = plan.get("action", "")
        raw = str(plan.get("input", "") or "")

        if action == "take_screenshot":
            return self._run_with_safety(lambda: self.registry.route_and_execute("take_screenshot", path=plan.get("path", "")), action)

        if action == "copy":
            result = self._run_with_safety(lambda: self.registry.execute("computer.clipboard_copy"), action)
            if isinstance(result, dict) and result.get("success"):
                clip = self.registry.execute("computer.clipboard_read")
                if isinstance(clip, dict) and clip.get("success"):
                    self.memory.add_clipboard_entry(clip.get("text", ""))
            return result

        if action == "paste" and raw.lower().strip() == "read clipboard":
            return self._run_with_safety(lambda: self.registry.execute("computer.clipboard_read"), action)

        if action == "paste":
            return self._run_with_safety(lambda: self.registry.execute("computer.clipboard_paste"), action)

        if action == "activate_window":
            title = raw.replace("activate window", "").replace("switch window", "").strip()
            return self._run_with_safety(lambda: self.registry.execute("computer.window_activate", title_contains=title), action)

        if action == "type":
            text = raw[5:] if raw.lower().startswith("type ") else raw
            interval = float(self.settings.get("typing_speed", 0.02))
            return self._run_with_safety(lambda: self.registry.execute("computer.keyboard_type", text=text, interval=interval), action)

        if action == "press":
            key = raw[6:].strip() if raw.lower().startswith("press ") else raw.strip()
            return self._run_with_safety(lambda: self.registry.execute("computer.press_key", key=key), action)

        if action == "hotkey":
            seq = raw.replace("hotkey", "").strip().replace("+", " ")
            keys = [k for k in seq.split() if k]
            return self._run_with_safety(lambda: self.registry.execute("computer.hotkeys", keys=keys), action)

        if action == "scroll":
            clicks = -500 if "down" in raw.lower() else 500
            return self._run_with_safety(lambda: self.registry.execute("computer.mouse_wheel_scroll", clicks=clicks), action)

        if action in {"click", "double_click", "right_click", "drag", "move_mouse", "computer_request"}:
            return self._run_with_safety(lambda: self.registry.route_and_execute("computer_request", input_text=raw), action)

        return {"success": False, "error": f"Unsupported computer action: {action}"}

    def _wait(self, seconds: float) -> Dict[str, Any]:
        bounded = max(0.0, min(float(seconds), 30.0))
        time.sleep(bounded)
        return {"success": True, "message": f"Waited {bounded:.2f} seconds"}

    def _ground_and_click(self, target: str) -> Dict[str, Any]:
        state = self.observer.get_latest_state() if self.observer else {}
        active_window = str(state.get("active_window", ""))
        analysis = state.get("last_analysis") if isinstance(state.get("last_analysis"), dict) else None
        attempts: List[Dict[str, Any]] = []

        for attempt in range(1, 4):
            grounded = self.grounder.ground(
                target,
                analysis=analysis,
                active_window=active_window,
                min_confidence=0.4,
            )
            if not grounded.get("success"):
                attempts.append({"attempt": attempt, "grounding": grounded})
                analysis = None
                continue

            coords = grounded.get("coordinates", {})
            x = int(coords.get("x", 0))
            y = int(coords.get("y", 0))
            clicked = self.registry.execute("computer.left_click", x=x, y=y)
            if clicked.get("success"):
                self.memory.add_clicked_element(grounded.get("label", target), x, y)

            # Verification: capture a fresh frame and keep top matches for diagnostics.
            verify_capture = self.vision.capture()
            verify = {"success": False}
            if verify_capture.get("success"):
                verify = self.vision.analyze(verify_capture.get("path", ""))

            attempts.append({
                "attempt": attempt,
                "grounding": grounded,
                "click": clicked,
                "verify": verify,
            })

            if clicked.get("success"):
                return {
                    "success": True,
                    "message": "Grounded and clicked target",
                    "grounding": grounded,
                    "click": clicked,
                    "verify": verify,
                    "attempts_log": attempts,
                }

            analysis = None

        return {
            "success": False,
            "error": "Unable to ground and click target",
            "target": target,
            "attempts_log": attempts,
        }

    def _run_with_safety(self, fn: Callable[[], Any], action_name: str) -> Dict[str, Any]:
        if self._cancel_requested:
            return {"success": False, "error": "Execution cancelled"}
        if self._emergency_stop:
            return {"success": False, "error": "Emergency stop active"}

        if self.dry_run_mode:
            return {"success": True, "dry_run": True, "action": action_name, "message": "Dry run: execution skipped"}

        if self.confirmation_mode:
            return {
                "success": True,
                "confirmation_required": True,
                "action": action_name,
                "message": "Confirmation mode: action prepared but not executed",
            }

        attempt = 0
        while attempt <= self.max_retries:
            attempt += 1
            result = self._run_with_timeout(fn, self.timeout_seconds)
            if isinstance(result, dict) and result.get("success"):
                self.memory.add_recent_task(action_name, status="completed")
                self.log.info("action=%s success attempt=%s", action_name, attempt)
                return result
            if attempt > self.max_retries:
                self.memory.add_recent_task(action_name, status="failed")
                self.log.error("action=%s failed attempts=%s result=%s", action_name, attempt, result)
                if isinstance(result, dict):
                    result["attempts"] = attempt
                    return result
                return {"success": False, "error": str(result), "attempts": attempt}

        return {"success": False, "error": "Execution failed"}

    def _run_with_timeout(self, fn: Callable[[], Any], timeout_seconds: int) -> Dict[str, Any]:
        container: Dict[str, Any] = {"result": None, "error": None}

        def _target():
            try:
                container["result"] = fn()
            except Exception as exc:
                container["error"] = str(exc)

        worker = threading.Thread(target=_target, daemon=True)
        worker.start()
        worker.join(timeout=max(1, int(timeout_seconds)))

        if worker.is_alive():
            return {"success": False, "error": f"Action timeout after {timeout_seconds} seconds"}

        if container["error"]:
            return {"success": False, "error": str(container["error"])}

        result = container["result"]
        if isinstance(result, dict):
            return result
        return {"success": True, "result": result}

    def _switch_model(self, model_name: str) -> Dict[str, Any]:
        """Switch the model if it exists locally in ollama."""
        if not model_name:
            return {"success": False, "error": "Model name not specified."}

        # Verify using subprocess 'ollama list'
        if not self._verify_model_installed(model_name):
            return {"success": False, "error": "Model not installed."}

        # Save to settings
        self.settings.set("llm_model", model_name)
        self.settings.save()
        return {"success": True, "model": model_name, "message": f"✓ Switched to {model_name}"}

    def _verify_model_installed(self, model_name: str) -> bool:
        """Run 'ollama list' to check if target model is present."""
        try:
            import subprocess
            res = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
            output = res.stdout.lower()
            model_lower = model_name.lower()
            lines = [line.split()[0] for line in output.splitlines() if line.strip() and not line.startswith("name")]
            return model_lower in lines or any(m.startswith(model_lower + ":") for m in lines)
        except Exception:
            return False
