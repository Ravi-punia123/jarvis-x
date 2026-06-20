"""JARVIS v1.4 Computer Agent — high-level computer-use orchestration.

Wraps tools/computer.py primitives with:
- OCR-based element location
- Image / template matching
- Per-action screen verification
- Automatic retry with back-off
- Structured event emission for UI streaming
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional

from logger import get_logger
from tool_registry import ToolRegistry

_log = get_logger("computer_agent")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(action: str, **kw: Any) -> Dict[str, Any]:
    return {"success": True, "action": action, **kw}


def _err(action: str, msg: str, **kw: Any) -> Dict[str, Any]:
    _log.error("action=%s error=%s", action, msg)
    return {"success": False, "action": action, "error": msg, **kw}


# ---------------------------------------------------------------------------
# ComputerAgent
# ---------------------------------------------------------------------------

class ComputerAgent:
    """High-level computer-use agent with verification and self-healing.

    All public methods return a structured result dict and optionally emit
    streaming events through ``stream_*`` generator equivalents.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        max_retries: int = 3,
        retry_delay: float = 0.8,
        verify_clicks: bool = True,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.max_retries = max(1, int(max_retries))
        self.retry_delay = max(0.1, float(retry_delay))
        self.verify_clicks = bool(verify_clicks)
        self.log = get_logger("computer_agent")

    # ------------------------------------------------------------------
    # Low-level primitives
    # ------------------------------------------------------------------

    def move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        """Move the mouse cursor to absolute screen coordinates."""
        return self._with_retry("move_mouse", lambda: self.registry.execute("computer.move_mouse", x=int(x), y=int(y)))

    def click(self, x: int, y: int, button: str = "left", verify: bool = True) -> Dict[str, Any]:
        """Click at coordinates; optionally capture a verification screenshot."""
        action = f"{button}_click"

        def _do() -> Dict[str, Any]:
            if button == "left":
                result = self.registry.execute("computer.left_click", x=int(x), y=int(y))
            elif button == "right":
                result = self.registry.execute("computer.right_click", x=int(x), y=int(y))
            elif button == "middle":
                result = self.registry.execute("computer.middle_click", x=int(x), y=int(y))
            else:
                return _err(action, f"Unknown button: {button}")
            if result.get("success") and verify and self.verify_clicks:
                snap = self.screenshot()
                result["verify_screenshot"] = snap.get("path", "")
            return result

        return self._with_retry(action, _do)

    def double_click(self, x: int, y: int) -> Dict[str, Any]:
        """Double-click at coordinates."""
        return self._with_retry("double_click", lambda: self.registry.execute("computer.double_click", x=int(x), y=int(y)))

    def right_click(self, x: int, y: int) -> Dict[str, Any]:
        """Right-click at coordinates."""
        return self.click(x, y, button="right")

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        """Scroll at current position or (x, y)."""
        def _do() -> Dict[str, Any]:
            if x is not None and y is not None:
                self.registry.execute("computer.move_mouse", x=int(x), y=int(y))
            return self.registry.execute("computer.mouse_wheel_scroll", clicks=int(clicks))

        return self._with_retry("scroll", _do)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.4) -> Dict[str, Any]:
        """Drag from (start_x, start_y) to (end_x, end_y)."""
        return self._with_retry(
            "drag",
            lambda: self.registry.execute(
                "computer.drag_and_drop",
                start_x=int(start_x), start_y=int(start_y),
                end_x=int(end_x), end_y=int(end_y),
                duration=float(duration),
            ),
        )

    def type_text(self, text: str, interval: float = 0.02) -> Dict[str, Any]:
        """Type text via keyboard."""
        return self._with_retry(
            "type_text",
            lambda: self.registry.execute("computer.keyboard_type", text=str(text), interval=float(interval)),
        )

    def press(self, key: str) -> Dict[str, Any]:
        """Press a single key."""
        return self._with_retry("press", lambda: self.registry.execute("computer.press_key", key=str(key)))

    def hotkey(self, *keys: str) -> Dict[str, Any]:
        """Execute a hotkey combination."""
        return self._with_retry("hotkey", lambda: self.registry.execute("computer.hotkeys", keys=list(keys)))

    def clipboard_copy(self) -> Dict[str, Any]:
        """Copy selection to clipboard."""
        return self._with_retry("clipboard_copy", lambda: self.registry.execute("computer.clipboard_copy"))

    def clipboard_paste(self) -> Dict[str, Any]:
        """Paste from clipboard."""
        return self._with_retry("clipboard_paste", lambda: self.registry.execute("computer.clipboard_paste"))

    def clipboard_read(self) -> Dict[str, Any]:
        """Read current clipboard text."""
        return self._with_retry("clipboard_read", lambda: self.registry.execute("computer.clipboard_read"))

    def clipboard_write(self, text: str) -> Dict[str, Any]:
        """Write text to clipboard using pyperclip."""
        try:
            import pyperclip
            pyperclip.copy(str(text))
            return _ok("clipboard_write", text_length=len(str(text)))
        except Exception as exc:
            return _err("clipboard_write", str(exc))

    # ------------------------------------------------------------------
    # Window management
    # ------------------------------------------------------------------

    def focus_window(self, title_contains: str) -> Dict[str, Any]:
        """Focus the first window whose title contains the given string."""
        return self._with_retry(
            "focus_window",
            lambda: self.registry.execute("computer.window_activate", title_contains=str(title_contains)),
        )

    def get_active_window(self) -> Dict[str, Any]:
        """Return metadata for the currently-active window."""
        return self.registry.execute("computer.get_active_window")

    def list_windows(self) -> Dict[str, Any]:
        """Return a list of all visible windows."""
        return self.registry.execute("computer.list_all_windows")

    def find_window(self, title_contains: str) -> Dict[str, Any]:
        """Search for and return metadata for a matching window."""
        result = self.list_windows()
        if not result.get("success"):
            return result
        needle = title_contains.lower()
        for win in result.get("windows", []):
            if needle in (win.get("title") or "").lower():
                return _ok("find_window", window=win)
        return _err("find_window", f"No window matching '{title_contains}'")

    # ------------------------------------------------------------------
    # Screenshot & OCR
    # ------------------------------------------------------------------

    def screenshot(self, path: str = "") -> Dict[str, Any]:
        """Capture the full screen and return the file path."""
        return self._with_retry(
            "screenshot",
            lambda: self.registry.execute("computer.take_screenshot", path=str(path)),
        )

    def ocr_screenshot(self) -> Dict[str, Any]:
        """Capture screen and return OCR text + bounding boxes."""
        snap = self.screenshot()
        if not snap.get("success"):
            return snap
        img_path = snap.get("path", "")
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(img_path)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            regions = []
            for idx, word in enumerate(data.get("text", [])):
                word = str(word).strip()
                if not word:
                    continue
                conf = float(str(data["conf"][idx]).strip() or "-1")
                if conf < 30:
                    continue
                regions.append(
                    {
                        "text": word,
                        "confidence": round(conf / 100, 3),
                        "bbox": {
                            "left": int(data["left"][idx]),
                            "top": int(data["top"][idx]),
                            "width": int(data["width"][idx]),
                            "height": int(data["height"][idx]),
                        },
                    }
                )
            return _ok("ocr_screenshot", path=img_path, regions=regions, region_count=len(regions))
        except Exception as exc:
            return _ok("ocr_screenshot", path=img_path, regions=[], region_count=0, ocr_error=str(exc))

    def find_text_on_screen(self, text: str) -> Dict[str, Any]:
        """Locate text on screen via OCR and return center coordinates."""
        result = self.ocr_screenshot()
        if not result.get("success"):
            return result
        needle = text.lower()
        for region in result.get("regions", []):
            if needle in region["text"].lower():
                bbox = region["bbox"]
                cx = bbox["left"] + bbox["width"] // 2
                cy = bbox["top"] + bbox["height"] // 2
                return _ok("find_text_on_screen", found=True, text=text, x=cx, y=cy, region=region)
        return _err("find_text_on_screen", f"Text '{text}' not found on screen")

    def click_text(self, text: str) -> Dict[str, Any]:
        """Find text on screen via OCR and click it."""
        locate = self.find_text_on_screen(text)
        if not locate.get("success"):
            return locate
        return self.click(locate["x"], locate["y"])

    # ------------------------------------------------------------------
    # Image / template matching
    # ------------------------------------------------------------------

    def find_image_on_screen(self, template_path: str, confidence: float = 0.8) -> Dict[str, Any]:
        """Locate a template image on the screen using pyautogui.locateOnScreen."""
        snap = self.screenshot()
        if not snap.get("success"):
            return snap
        try:
            import pyautogui
            location = pyautogui.locateOnScreen(str(template_path), confidence=float(confidence))
            if location is None:
                return _err("find_image_on_screen", f"Template '{template_path}' not found")
            cx = int(location.left + location.width // 2)
            cy = int(location.top + location.height // 2)
            return _ok(
                "find_image_on_screen",
                found=True,
                template=template_path,
                x=cx,
                y=cy,
                bbox={"left": int(location.left), "top": int(location.top), "width": int(location.width), "height": int(location.height)},
            )
        except Exception as exc:
            return _err("find_image_on_screen", str(exc), template=template_path)

    def click_image(self, template_path: str, confidence: float = 0.8) -> Dict[str, Any]:
        """Find a template image on screen and click it."""
        locate = self.find_image_on_screen(template_path, confidence)
        if not locate.get("success"):
            return locate
        return self.click(locate["x"], locate["y"])

    # ------------------------------------------------------------------
    # Screen verification
    # ------------------------------------------------------------------

    def verify_text_present(self, text: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Poll OCR until `text` appears on screen or timeout expires."""
        deadline = time.time() + max(0.5, float(timeout))
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            result = self.find_text_on_screen(text)
            if result.get("success"):
                return _ok("verify_text_present", text=text, found=True, attempts=attempt)
            time.sleep(0.5)
        return _err("verify_text_present", f"Text '{text}' not found within {timeout}s", attempts=attempt)

    def verify_window_open(self, title_contains: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Poll window list until a matching window appears."""
        deadline = time.time() + max(0.5, float(timeout))
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            result = self.find_window(title_contains)
            if result.get("success"):
                return _ok("verify_window_open", title_contains=title_contains, found=True, attempts=attempt)
            time.sleep(0.5)
        return _err("verify_window_open", f"Window '{title_contains}' not found within {timeout}s", attempts=attempt)

    # ------------------------------------------------------------------
    # Streaming (generator) interface
    # ------------------------------------------------------------------

    def stream_click_text(self, text: str) -> Generator[Dict[str, Any], None, None]:
        """Stream events while clicking text on screen."""
        yield {"event": "thinking", "message": f"Looking for '{text}' on screen"}
        locate = self.find_text_on_screen(text)
        if not locate.get("success"):
            yield {"event": "error", "message": locate.get("error", "not found")}
            return
        yield {"event": "found", "message": f"Found '{text}' at ({locate['x']}, {locate['y']})"}
        result = self.click(locate["x"], locate["y"])
        yield {"event": "done" if result.get("success") else "error", "result": result, "message": result.get("message", result.get("error", ""))}

    def stream_run(self, steps: List[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        """Execute a list of step dicts, yielding progress events.

        Each step dict: {"action": str, ...kwargs}
        """
        total = len(steps)
        yield {"event": "start", "total": total}
        for idx, step in enumerate(steps, 1):
            action = step.get("action", "")
            yield {"event": "step_start", "step": idx, "total": total, "action": action}
            result = self.execute_step(step)
            yield {
                "event": "step_result",
                "step": idx,
                "total": total,
                "action": action,
                "success": result.get("success", False),
                "result": result,
            }
            if not result.get("success"):
                yield {"event": "failed", "step": idx, "error": result.get("error", "unknown")}
                return
        yield {"event": "finished", "total": total}

    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step dict."""
        action = str(step.get("action", "")).strip()
        dispatch: Dict[str, Callable[..., Dict[str, Any]]] = {
            "click": lambda s: self.click(int(s.get("x", 0)), int(s.get("y", 0)), s.get("button", "left")),
            "double_click": lambda s: self.double_click(int(s.get("x", 0)), int(s.get("y", 0))),
            "right_click": lambda s: self.right_click(int(s.get("x", 0)), int(s.get("y", 0))),
            "move_mouse": lambda s: self.move_mouse(int(s.get("x", 0)), int(s.get("y", 0))),
            "scroll": lambda s: self.scroll(int(s.get("clicks", -500)), s.get("x"), s.get("y")),
            "drag": lambda s: self.drag(int(s.get("start_x", 0)), int(s.get("start_y", 0)), int(s.get("end_x", 0)), int(s.get("end_y", 0))),
            "type_text": lambda s: self.type_text(str(s.get("text", ""))),
            "press": lambda s: self.press(str(s.get("key", ""))),
            "hotkey": lambda s: self.hotkey(*s.get("keys", [])),
            "screenshot": lambda s: self.screenshot(str(s.get("path", ""))),
            "ocr": lambda _s: self.ocr_screenshot(),
            "find_text": lambda s: self.find_text_on_screen(str(s.get("text", ""))),
            "click_text": lambda s: self.click_text(str(s.get("text", ""))),
            "focus_window": lambda s: self.focus_window(str(s.get("title", ""))),
            "verify_text": lambda s: self.verify_text_present(str(s.get("text", "")), float(s.get("timeout", 5.0))),
            "verify_window": lambda s: self.verify_window_open(str(s.get("title", "")), float(s.get("timeout", 5.0))),
            "clipboard_copy": lambda _s: self.clipboard_copy(),
            "clipboard_paste": lambda _s: self.clipboard_paste(),
            "clipboard_read": lambda _s: self.clipboard_read(),
            "clipboard_write": lambda s: self.clipboard_write(str(s.get("text", ""))),
            "wait": lambda s: self._wait(float(s.get("seconds", 1.0))),
        }
        fn = dispatch.get(action)
        if fn is None:
            return _err(action, f"Unknown computer_agent action: '{action}'")
        return fn(step)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _with_retry(self, action: str, fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        """Run fn up to max_retries times, returning on first success."""
        last: Dict[str, Any] = {}
        for attempt in range(1, self.max_retries + 1):
            t0 = time.perf_counter()
            result = fn()
            elapsed = round(time.perf_counter() - t0, 4)
            if result.get("success"):
                if attempt > 1:
                    self.log.info("action=%s recovered on attempt=%s latency=%.3fs", action, attempt, elapsed)
                else:
                    self.log.debug("action=%s ok latency=%.3fs", action, elapsed)
                result["attempt"] = attempt
                result["latency_seconds"] = elapsed
                return result
            last = result
            self.log.warning("action=%s attempt=%s/%s failed: %s", action, attempt, self.max_retries, result.get("error", ""))
            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)
        last["attempts"] = self.max_retries
        return last

    @staticmethod
    def _wait(seconds: float) -> Dict[str, Any]:
        bounded = max(0.0, min(float(seconds), 60.0))
        time.sleep(bounded)
        return _ok("wait", seconds=bounded)
