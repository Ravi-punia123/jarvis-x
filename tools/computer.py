"""Computer control toolkit for mouse, keyboard, clipboard, window, and display actions."""

from __future__ import annotations

import ctypes
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _ok(action: str, **payload: Any) -> Dict[str, Any]:
    return {"success": True, "action": action, **payload}


def _error(action: str, message: str, **payload: Any) -> Dict[str, Any]:
    return {"success": False, "action": action, "error": message, **payload}


def _require_pyautogui(action: str):
    try:
        import pyautogui

        pyautogui.FAILSAFE = True
        return pyautogui, None
    except Exception as exc:
        return None, _error(action, f"pyautogui unavailable: {exc}")


def _window_to_dict(win) -> Dict[str, Any]:
    return {
        "title": getattr(win, "title", ""),
        "left": int(getattr(win, "left", 0)),
        "top": int(getattr(win, "top", 0)),
        "width": int(getattr(win, "width", 0)),
        "height": int(getattr(win, "height", 0)),
        "is_active": bool(getattr(win, "isActive", False)),
        "is_minimized": bool(getattr(win, "isMinimized", False)),
        "is_maximized": bool(getattr(win, "isMaximized", False)),
    }


def _find_window(title_contains: str):
    try:
        import pygetwindow as gw
    except Exception:
        return None

    needle = (title_contains or "").strip().lower()
    windows = gw.getAllWindows()
    if not needle:
        return gw.getActiveWindow()

    for win in windows:
        if needle in (win.title or "").lower():
            return win
    return None


def move_mouse(x: int, y: int, duration: float = 0.0) -> Dict[str, Any]:
    action = "move_mouse"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        pyautogui.moveTo(int(x), int(y), duration=max(0.0, float(duration)))
        return _ok(action, x=int(x), y=int(y), duration=float(duration))
    except Exception as exc:
        return _error(action, str(exc))


def left_click(x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    return _click("left_click", "left", x, y)


def right_click(x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    return _click("right_click", "right", x, y)


def middle_click(x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    return _click("middle_click", "middle", x, y)


def double_click(x: Optional[int] = None, y: Optional[int] = None, interval: float = 0.2) -> Dict[str, Any]:
    action = "double_click"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        kwargs: Dict[str, Any] = {"interval": max(0.01, float(interval))}
        if x is not None and y is not None:
            kwargs["x"] = int(x)
            kwargs["y"] = int(y)
        pyautogui.doubleClick(**kwargs)
        return _ok(action, x=x, y=y, interval=float(interval))
    except Exception as exc:
        return _error(action, str(exc))


def _click(action: str, button: str, x: Optional[int], y: Optional[int]) -> Dict[str, Any]:
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        kwargs: Dict[str, Any] = {"button": button}
        if x is not None and y is not None:
            kwargs["x"] = int(x)
            kwargs["y"] = int(y)
        pyautogui.click(**kwargs)
        return _ok(action, button=button, x=x, y=y)
    except Exception as exc:
        return _error(action, str(exc))


def drag_and_drop(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.4) -> Dict[str, Any]:
    action = "drag_and_drop"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        pyautogui.moveTo(int(start_x), int(start_y))
        pyautogui.dragTo(int(end_x), int(end_y), duration=max(0.01, float(duration)), button="left")
        return _ok(
            action,
            start={"x": int(start_x), "y": int(start_y)},
            end={"x": int(end_x), "y": int(end_y)},
            duration=float(duration),
        )
    except Exception as exc:
        return _error(action, str(exc))


def mouse_wheel_scroll(clicks: int) -> Dict[str, Any]:
    action = "mouse_wheel_scroll"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        pyautogui.scroll(int(clicks))
        return _ok(action, clicks=int(clicks))
    except Exception as exc:
        return _error(action, str(exc))


def keyboard_type(text: str, interval: float = 0.02) -> Dict[str, Any]:
    action = "keyboard_type"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        pyautogui.write(str(text), interval=max(0.0, float(interval)))
        return _ok(action, typed_length=len(str(text)), interval=float(interval))
    except Exception as exc:
        return _error(action, str(exc))


def hotkeys(keys: List[str]) -> Dict[str, Any]:
    action = "hotkeys"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        clean = [str(k).lower().strip() for k in keys if str(k).strip()]
        if not clean:
            return _error(action, "No keys provided")
        pyautogui.hotkey(*clean)
        return _ok(action, keys=clean)
    except Exception as exc:
        return _error(action, str(exc))


def press_key(key: str) -> Dict[str, Any]:
    action = "press_key"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        pyautogui.press(str(key).lower())
        return _ok(action, key=str(key).lower())
    except Exception as exc:
        return _error(action, str(exc))


def hold_key(key: str) -> Dict[str, Any]:
    action = "hold_key"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        pyautogui.keyDown(str(key).lower())
        return _ok(action, key=str(key).lower())
    except Exception as exc:
        return _error(action, str(exc))


def release_key(key: str) -> Dict[str, Any]:
    action = "release_key"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        pyautogui.keyUp(str(key).lower())
        return _ok(action, key=str(key).lower())
    except Exception as exc:
        return _error(action, str(exc))


def clipboard_copy() -> Dict[str, Any]:
    action = "clipboard_copy"
    return hotkeys(["ctrl", "c"]) | {"action": action}


def clipboard_paste() -> Dict[str, Any]:
    action = "clipboard_paste"
    return hotkeys(["ctrl", "v"]) | {"action": action}


def clipboard_read() -> Dict[str, Any]:
    action = "clipboard_read"
    try:
        import pyperclip

        text = pyperclip.paste()
        return _ok(action, text=str(text), length=len(str(text)))
    except Exception as exc:
        return _error(action, f"clipboard unavailable: {exc}")


def window_focus(title_contains: str) -> Dict[str, Any]:
    return window_activate(title_contains)


def window_activate(title_contains: str) -> Dict[str, Any]:
    action = "window_activate"
    try:
        win = _find_window(title_contains)
        if not win:
            return _error(action, "Window not found", query=title_contains)
        win.activate()
        return _ok(action, query=title_contains, window=_window_to_dict(win))
    except Exception as exc:
        return _error(action, str(exc), query=title_contains)


def window_minimize(title_contains: str) -> Dict[str, Any]:
    action = "window_minimize"
    try:
        win = _find_window(title_contains)
        if not win:
            return _error(action, "Window not found", query=title_contains)
        win.minimize()
        return _ok(action, query=title_contains, window=_window_to_dict(win))
    except Exception as exc:
        return _error(action, str(exc), query=title_contains)


def window_maximize(title_contains: str) -> Dict[str, Any]:
    action = "window_maximize"
    try:
        win = _find_window(title_contains)
        if not win:
            return _error(action, "Window not found", query=title_contains)
        win.maximize()
        return _ok(action, query=title_contains, window=_window_to_dict(win))
    except Exception as exc:
        return _error(action, str(exc), query=title_contains)


def window_close(title_contains: str) -> Dict[str, Any]:
    action = "window_close"
    try:
        win = _find_window(title_contains)
        if not win:
            return _error(action, "Window not found", query=title_contains)
        win.close()
        return _ok(action, query=title_contains, closed=True)
    except Exception as exc:
        return _error(action, str(exc), query=title_contains)


def window_resize(title_contains: str, width: int, height: int) -> Dict[str, Any]:
    action = "window_resize"
    try:
        win = _find_window(title_contains)
        if not win:
            return _error(action, "Window not found", query=title_contains)
        win.resizeTo(int(width), int(height))
        return _ok(action, query=title_contains, width=int(width), height=int(height), window=_window_to_dict(win))
    except Exception as exc:
        return _error(action, str(exc), query=title_contains)


def get_active_window() -> Dict[str, Any]:
    action = "get_active_window"
    try:
        import pygetwindow as gw

        win = gw.getActiveWindow()
        if not win:
            return _error(action, "No active window")
        return _ok(action, window=_window_to_dict(win))
    except Exception as exc:
        return _error(action, f"window manager unavailable: {exc}")


def list_all_windows(limit: int = 100) -> Dict[str, Any]:
    action = "list_all_windows"
    try:
        import pygetwindow as gw

        windows = []
        for win in gw.getAllWindows():
            title = (win.title or "").strip()
            if title:
                windows.append(_window_to_dict(win))
            if len(windows) >= max(1, int(limit)):
                break
        return _ok(action, windows=windows, count=len(windows))
    except Exception as exc:
        return _error(action, f"window manager unavailable: {exc}")


def take_screenshot(path: str = "") -> Dict[str, Any]:
    action = "take_screenshot"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        output = Path(path.strip()) if path else Path.cwd() / f"jarvis_capture_{int(time.time())}.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        image = pyautogui.screenshot()
        image.save(output)
        return _ok(action, path=str(output.resolve()))
    except Exception as exc:
        return _error(action, str(exc))


def locate_screen_size() -> Dict[str, Any]:
    action = "locate_screen_size"
    try:
        user32 = ctypes.windll.user32
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        return _ok(action, width=width, height=height)
    except Exception as exc:
        return _error(action, str(exc))


def current_mouse_position() -> Dict[str, Any]:
    action = "current_mouse_position"
    pyautogui, err = _require_pyautogui(action)
    if err:
        return err

    try:
        x, y = pyautogui.position()
        return _ok(action, x=int(x), y=int(y))
    except Exception as exc:
        return _error(action, str(exc))
