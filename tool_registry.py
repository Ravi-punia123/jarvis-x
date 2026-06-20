"""Dynamic tool discovery and execution adapters."""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolSpec:
    name: str
    description: str
    capabilities: List[str]
    parameters: List[str]
    examples: List[str]
    fn: Callable[..., Any]


class ToolRegistry:
    """Discovers tool callables from the tools package."""

    def __init__(self, tools_package: str = "tools"):
        self.tools_package = tools_package
        self._tools: Dict[str, ToolSpec] = {}
        self.discover()

    def discover(self) -> None:
        self._tools = {}
        root = Path(__file__).parent / "tools"
        for file in root.glob("*.py"):
            if file.name.startswith("__"):
                continue
            module_name = f"{self.tools_package}.{file.stem}"
            module = importlib.import_module(module_name)
            for name, member in inspect.getmembers(module, inspect.isfunction):
                if name.startswith("_"):
                    continue
                signature = inspect.signature(member)
                params = list(signature.parameters.keys())
                doc = (member.__doc__ or "").strip()
                key = f"{file.stem}.{name}"
                self._tools[key] = ToolSpec(
                    name=key,
                    description=doc or f"Tool function {name}",
                    capabilities=[file.stem, name],
                    parameters=params,
                    examples=[f"Use {name} with parameters: {', '.join(params)}"],
                    fn=member,
                )

    def list_tools(self) -> List[ToolSpec]:
        return sorted(self._tools.values(), key=lambda t: t.name)

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def execute(self, name: str, **kwargs: Any) -> Any:
        tool = self.get(name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {name}"}
        return tool.fn(**kwargs)

    def route_and_execute(self, action: str, input_text: str = "", path: str = "") -> Any:
        lowered = (input_text or "").strip().lower()

        if action == "open_app":
            return self.execute("desktop.open_application", app_name=input_text)

        if action == "browser_request":
            if lowered.startswith("search "):
                return self.execute("browser.search_google", query=input_text[7:].strip())
            target = input_text[5:].strip() if lowered.startswith("open ") else input_text
            return self.execute("browser.open_url", url=target)

        if action == "file_request":
            if lowered.startswith("find "):
                return self.execute("filesystem.find_file", filename=input_text[5:].strip())
            if lowered.startswith("list "):
                return self.execute("filesystem.list_directory", path=input_text[5:].strip())
            if lowered.startswith("create folder "):
                return self.execute("filesystem.create_folder", path=input_text[len("create folder "):].strip())
            if lowered.startswith("create file "):
                payload = input_text[len("create file "):].strip()
                if " content " in payload.lower():
                    idx = payload.lower().find(" content ")
                    return self.execute(
                        "filesystem.create_text_file",
                        path=payload[:idx].strip(),
                        content=payload[idx + len(" content "):],
                    )
                return self.execute("filesystem.create_text_file", path=payload, content="")
            if lowered.startswith("read "):
                return self.execute("filesystem.read_text_file", path=input_text[5:].strip())

        if action == "create_folder":
            return self.execute("filesystem.create_folder", path=path)

        if action == "computer_request":
            return self._route_computer(lowered, input_text)

        if action == "take_screenshot":
            return self.execute("computer.take_screenshot", path=path)

        return {"success": False, "error": f"No tool route for action: {action}"}

    def _route_computer(self, lowered: str, raw_input: str) -> Any:
        if lowered.startswith("click "):
            x, y = self._extract_xy(lowered)
            if x is not None and y is not None:
                return self.execute("computer.left_click", x=x, y=y)

        if lowered.startswith("double click"):
            x, y = self._extract_xy(lowered)
            if x is not None and y is not None:
                return self.execute("computer.double_click", x=x, y=y)
            return self.execute("computer.double_click")

        if lowered.startswith("right click"):
            x, y = self._extract_xy(lowered)
            if x is not None and y is not None:
                return self.execute("computer.right_click", x=x, y=y)
            return self.execute("computer.right_click")

        if lowered.startswith("scroll down"):
            return self.execute("computer.mouse_wheel_scroll", clicks=-500)

        if lowered.startswith("scroll up"):
            return self.execute("computer.mouse_wheel_scroll", clicks=500)

        if lowered.startswith("type "):
            return self.execute("computer.keyboard_type", text=raw_input[5:])

        if lowered.startswith("press "):
            return self.execute("computer.press_key", key=raw_input[6:].strip())

        if lowered.startswith("hotkey "):
            keys = [k.strip() for k in raw_input[7:].replace("+", " ").split() if k.strip()]
            return self.execute("computer.hotkeys", keys=keys)

        if lowered.startswith("copy"):
            return self.execute("computer.clipboard_copy")

        if lowered.startswith("paste"):
            return self.execute("computer.clipboard_paste")

        if lowered.startswith("read clipboard"):
            return self.execute("computer.clipboard_read")

        if lowered.startswith("switch window") or lowered.startswith("activate window"):
            title = raw_input.split(" ", 2)[-1] if " " in raw_input else ""
            return self.execute("computer.window_activate", title_contains=title)

        if lowered.startswith("close "):
            return self.execute("computer.window_close", title_contains=raw_input[6:].strip())

        if lowered.startswith("screenshot") or lowered.startswith("take screenshot"):
            return self.execute("computer.take_screenshot")

        return {"success": False, "error": f"No computer route for input: {raw_input}"}

    def _extract_xy(self, text: str) -> tuple[Optional[int], Optional[int]]:
        parts = text.replace(",", " ").split()
        numbers: List[int] = []
        for part in parts:
            try:
                numbers.append(int(part))
            except ValueError:
                continue
        if len(numbers) >= 2:
            return numbers[0], numbers[1]
        return None, None
