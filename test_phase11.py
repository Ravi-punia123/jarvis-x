import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from executor import Executor
from memory import MemoryManager
from planner import Planner
from settings_manager import SettingsManager
from task_queue import TaskQueue
from tool_registry import ToolRegistry
from ui_history import HistoryManager
from vision import VisionManager


class TestPlannerRouting(unittest.TestCase):
    def setUp(self):
        self.planner = Planner()

    def test_open_app_route(self):
        plan = self.planner.plan("open notepad")
        self.assertEqual(plan["action"], "open_app")
        self.assertEqual(plan["module"], "desktop_tools")

    def test_browser_route(self):
        plan = self.planner.plan("search what is python")
        self.assertEqual(plan["action"], "skill_call")
        self.assertEqual(plan["skill"], "browser")
        self.assertEqual(plan["intent"], "browser_request")

    def test_screen_analysis_route(self):
        plan = self.planner.plan("what is on my screen")
        self.assertEqual(plan["action"], "analyze_screen")
        self.assertEqual(plan["module"], "vision")

    def test_pipeline_route(self):
        plan = self.planner.plan("create folder tmp_test then open it")
        self.assertIsInstance(plan, list)
        self.assertEqual(plan[0]["action"], "create_folder")
        self.assertEqual(plan[1]["action"], "open_folder")


class TestSettingsPersistence(unittest.TestCase):
    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings = SettingsManager(str(settings_path))
            settings.update({"temperature": 0.7, "llm_model": "qwen3:14b"})
            settings.save()

            reloaded = SettingsManager(str(settings_path))
            self.assertEqual(reloaded.get("temperature"), 0.7)
            self.assertEqual(reloaded.get("llm_model"), "qwen3:14b")
            self.assertIn("vision_model", reloaded.all())


class TestMemoryManager(unittest.TestCase):
    def test_memory_search_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory_path = Path(tmp) / "memory.json"
            memory = MemoryManager(str(memory_path), recent_limit=10, long_term_limit=200, session_limit=100)
            memory.add_user_message("What is Python?")
            memory.add_assistant_message("Python is a programming language.")
            memory.add_action("search", {"query": "python"})
            memory.add_long_term_fact("User likes automation", tags=["preference"])

            found = memory.search_memory("python")
            self.assertGreaterEqual(len(found["messages"]), 1)
            self.assertGreaterEqual(len(found["actions"]), 1)

            summary = memory.summarize_memory()
            self.assertIn("Python", summary)

            recent = memory.get_recent_context(5)
            self.assertGreaterEqual(len(recent), 2)


class TestHistoryManager(unittest.TestCase):
    def test_export_import_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            history_path = Path(tmp) / "chat_history.json"
            export_path = Path(tmp) / "session_export.json"

            history = HistoryManager(str(history_path))
            history.new_session("Test")
            history.add_message("user", "hello", {})
            history.add_message("assistant", "hi", {})
            history.save_session("Session A")

            exported = history.export_session(0, format="json")
            self.assertIsNotNone(exported)
            export_path.write_text(exported, encoding="utf-8")

            imported_ok = history.import_session(str(export_path))
            self.assertTrue(imported_ok)
            sessions = history.get_sessions()
            self.assertEqual(len(sessions), 2)
            self.assertEqual(sessions[1]["id"], 1)


class TestTaskQueue(unittest.TestCase):
    def test_queue_events_and_retry(self):
        queue = TaskQueue()
        events = []

        def callback(name, payload):
            events.append((name, payload))

        queue.register_callback("test", callback)

        task_id = queue.submit("unit-task", lambda: {"ok": True})
        self.assertTrue(task_id)

        deadline = time.time() + 3
        while time.time() < deadline and not any(name == "completed" for name, _ in events):
            time.sleep(0.05)

        self.assertTrue(any(name == "queued" for name, _ in events))
        self.assertTrue(any(name == "started" for name, _ in events))
        self.assertTrue(any(name == "completed" for name, _ in events))

        retry_id = queue.retry_latest()
        self.assertTrue(retry_id)

        queue.shutdown()


class TestToolRegistry(unittest.TestCase):
    def test_discovery_and_filesystem_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools = ToolRegistry()
            names = [spec.name for spec in tools.list_tools()]
            self.assertIn("filesystem.create_folder", names)
            self.assertIn("browser.open_url", names)
            self.assertIn("desktop.open_application", names)

            Path(tmp).mkdir(parents=True, exist_ok=True)
            # Route file operations through discovered tools.
            result = tools.execute("filesystem.create_text_file", path=str(Path(tmp) / "note.txt"), content="ok")
            self.assertTrue(result.get("success"))

            read_result = tools.execute("filesystem.read_text_file", path=str(Path(tmp) / "note.txt"))
            self.assertTrue(read_result.get("success"))
            self.assertEqual(read_result.get("content"), "ok")


class TestVisionManager(unittest.TestCase):
    def test_timeout_and_json_parse(self):
        vm = VisionManager()
        vm.set_timeout(10)
        self.assertGreaterEqual(vm.timeout_seconds, 30)

        parsed = vm._parse_json('{"windows": ["Editor"], "buttons": ["Run"], "text": ["hello"]}')
        self.assertEqual(parsed["windows"], ["Editor"])
        self.assertEqual(parsed["buttons"], ["Run"])
        self.assertEqual(parsed["text"], ["hello"])


class TestExecutor(unittest.TestCase):
    def test_execute_create_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "new_folder")
            executor = Executor()
            result = executor.execute({"action": "create_folder", "path": target})
            self.assertTrue(result.get("success"))
            self.assertTrue(Path(target).exists())

    def test_execute_open_app_and_browser(self):
        executor = Executor()
        with patch.object(executor.registry, "route_and_execute", return_value={"success": True, "message": "ok"}) as mock_route:
            app_result = executor.execute({"action": "open_app", "module": "desktop_tools", "input": "open notepad"})
            browser_result = executor.execute({"action": "browser_request", "module": "browser_tools", "input": "search python"})
            self.assertTrue(app_result.get("success"))
            self.assertTrue(browser_result.get("success"))
            self.assertEqual(mock_route.call_count, 2)

    def test_execute_analyze_screen(self):
        executor = Executor()
        with patch.object(executor.vision, "capture", return_value={"success": True, "path": "sample.png"}):
            with patch.object(executor.vision, "analyze", return_value={"success": True, "message": "analysis"}):
                result = executor.execute({"action": "analyze_screen", "module": "vision", "input": "what is on my screen"})
                self.assertTrue(result.get("success"))


if __name__ == "__main__":
    unittest.main()
