import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from executor import Executor
from observer import Observer
from planner import Planner
from screen_grounding import ScreenGrounder
from tool_registry import ToolRegistry
from tools import computer


class TestComputerToolkit(unittest.TestCase):
    def test_mouse_and_keyboard_actions(self):
        fake_gui = SimpleNamespace(
            FAILSAFE=True,
            moveTo=MagicMock(),
            click=MagicMock(),
            doubleClick=MagicMock(),
            scroll=MagicMock(),
            write=MagicMock(),
            hotkey=MagicMock(),
            press=MagicMock(),
            keyDown=MagicMock(),
            keyUp=MagicMock(),
            position=lambda: (100, 200),
            screenshot=MagicMock(return_value=SimpleNamespace(save=MagicMock())),
            dragTo=MagicMock(),
        )

        with patch("tools.computer._require_pyautogui", return_value=(fake_gui, None)):
            self.assertTrue(computer.move_mouse(10, 20).get("success"))
            self.assertTrue(computer.left_click(10, 20).get("success"))
            self.assertTrue(computer.double_click().get("success"))
            self.assertTrue(computer.mouse_wheel_scroll(-100).get("success"))
            self.assertTrue(computer.keyboard_type("hello").get("success"))
            self.assertTrue(computer.hotkeys(["ctrl", "c"]).get("success"))
            self.assertTrue(computer.press_key("enter").get("success"))
            self.assertTrue(computer.hold_key("shift").get("success"))
            self.assertTrue(computer.release_key("shift").get("success"))
            self.assertTrue(computer.current_mouse_position().get("success"))

    def test_clipboard_and_window_actions(self):
        fake_window = SimpleNamespace(
            title="Notepad",
            left=0,
            top=0,
            width=800,
            height=600,
            isActive=True,
            isMinimized=False,
            isMaximized=False,
            activate=MagicMock(),
            minimize=MagicMock(),
            maximize=MagicMock(),
            close=MagicMock(),
            resizeTo=MagicMock(),
        )
        fake_gw = SimpleNamespace(
            getAllWindows=lambda: [fake_window],
            getActiveWindow=lambda: fake_window,
        )

        with patch.dict("sys.modules", {"pygetwindow": fake_gw}):
            self.assertTrue(computer.window_activate("note").get("success"))
            self.assertTrue(computer.window_minimize("note").get("success"))
            self.assertTrue(computer.window_maximize("note").get("success"))
            self.assertTrue(computer.window_resize("note", 640, 480).get("success"))
            self.assertTrue(computer.list_all_windows().get("success"))
            self.assertTrue(computer.get_active_window().get("success"))

        with patch("tools.computer.hotkeys", return_value={"success": True}):
            self.assertTrue(computer.clipboard_copy().get("success"))
            self.assertTrue(computer.clipboard_paste().get("success"))

        fake_clip = SimpleNamespace(paste=lambda: "sample")
        with patch.dict("sys.modules", {"pyperclip": fake_clip}):
            out = computer.clipboard_read()
            self.assertTrue(out.get("success"))
            self.assertEqual(out.get("text"), "sample")


class TestPlannerV12(unittest.TestCase):
    def test_computer_actions_and_pipeline(self):
        planner = Planner()
        single = planner.plan("click 100 200")
        self.assertEqual(single["module"], "computer_tools")

        multi = planner.plan("Open Chrome, search OpenAI, click first result")
        self.assertIsInstance(multi, dict)
        self.assertEqual(multi.get("action"), "autonomous_loop")
        self.assertGreaterEqual(len(multi.get("steps", [])), 3)


class TestExecutorV12(unittest.TestCase):
    def test_executor_safety_modes_and_computer_dispatch(self):
        ex = Executor()

        dry = ex.set_mode("dry_run")
        self.assertTrue(dry.get("success"))
        out = ex.execute({"action": "click", "module": "computer_tools", "input": "click 12 34"})
        self.assertTrue(out.get("success"))
        self.assertTrue(out.get("dry_run"))

        ex.set_mode("real")
        with patch.object(ex.registry, "route_and_execute", return_value={"success": True, "message": "clicked"}):
            out = ex.execute({"action": "computer_request", "module": "computer_tools", "input": "click 12 34"})
            self.assertTrue(out.get("success"))

        ex.emergency_stop()
        blocked = ex.execute({"action": "click", "module": "computer_tools", "input": "click 12 34"})
        self.assertFalse(blocked.get("success"))
        ex.clear_emergency_stop()


class TestGrounding(unittest.TestCase):
    def test_ground_target(self):
        grounder = ScreenGrounder()
        analysis = {
            "window_titles": [{"title": "Google Chrome", "bounding_box": {"left": 0, "top": 0, "width": 1000, "height": 700}}],
            "buttons": [{"label": "Send", "bounding_box": {"left": 300, "top": 500, "width": 80, "height": 30}}],
            "text_regions": [{"text": "Address bar", "bounding_box": {"left": 120, "top": 50, "width": 600, "height": 30}}],
            "ui_elements": [{"type": "icon", "label": "Search icon", "bounding_box": {"left": 760, "top": 52, "width": 24, "height": 24}}],
        }
        out = grounder.ground("search icon", analysis=analysis)
        self.assertTrue(out.get("success"))
        self.assertEqual(out.get("element_type"), "icon")


class TestObserver(unittest.TestCase):
    def test_observer_loop_capture(self):
        fake_vision = SimpleNamespace(
            capture=lambda: {"success": True, "path": "sample.png"},
            analyze_image=lambda *_args, **_kwargs: {"success": True, "data": {"ui_elements": []}},
        )
        fake_memory = SimpleNamespace(
            set_last_active_window=MagicMock(),
            add_window_history=MagicMock(),
            add_recent_screenshot=MagicMock(),
        )
        fake_registry = SimpleNamespace(execute=lambda *_args, **_kwargs: {"success": True, "window": {"title": "Notepad"}})

        observer = Observer(vision=fake_vision, memory=fake_memory, registry=fake_registry, interval_seconds=0.1)
        started = observer.start()
        self.assertTrue(started.get("success"))
        time.sleep(0.25)
        state = observer.get_latest_state()
        self.assertEqual(state.get("active_window"), "Notepad")
        self.assertEqual(state.get("last_screenshot"), "sample.png")
        observer.stop()


class TestToolRegistryComputerRoute(unittest.TestCase):
    def test_computer_routing(self):
        registry = ToolRegistry()
        with patch.object(registry, "execute", return_value={"success": True, "message": "ok"}) as mock_exec:
            out = registry.route_and_execute("computer_request", input_text="type hello")
            self.assertTrue(out.get("success"))
            self.assertTrue(mock_exec.called)


if __name__ == "__main__":
    unittest.main()
