import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from executor import Executor
from goal_manager import GoalManager
from memory import MemoryManager
from planner import Planner
from reasoner import Reasoner
from screen_grounding import ScreenGrounder


class TestGoalAndReasonerV13(unittest.TestCase):
    def test_goal_order_and_reasoning(self):
        gm = GoalManager()
        goals = gm.create_goals("open browser then search docs then summarize")
        ordered = gm.ordered(goals)
        self.assertGreaterEqual(len(ordered), 2)
        self.assertEqual(ordered[0].id, "g1")

        reasoner = Reasoner()
        strategy = reasoner.reason("search python docs", {"active_window": "Chrome"})
        self.assertIn("goals", strategy)
        self.assertIn("execution_order", strategy)


class TestPlannerSkillsV13(unittest.TestCase):
    def test_skill_routing(self):
        planner = Planner()

        browser = planner.plan("search best python testing practices")
        self.assertEqual(browser.get("action"), "skill_call")
        self.assertEqual(browser.get("skill"), "browser")

        gh = planner.plan("git status")
        self.assertEqual(gh.get("skill"), "github")

        fs = planner.plan("create file notes.txt")
        self.assertEqual(fs.get("skill"), "filesystem")


class TestExecutorSkillsV13(unittest.TestCase):
    def test_executor_dispatches_skill(self):
        ex = Executor()
        with patch.object(ex.skills, "execute", return_value={"success": True, "message": "ok"}) as mock_skill:
            out = ex.execute({"action": "skill_call", "module": "skills", "skill": "browser", "input": "search llm"})
            self.assertTrue(out.get("success"))
            self.assertTrue(mock_skill.called)


class TestMemorySemanticV13(unittest.TestCase):
    def test_semantic_search_and_entities(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem_file = Path(tmp) / "memory.json"
            mem = MemoryManager(file_path=str(mem_file))
            mem.add_user_message("Need python test plan")
            mem.add_goal("Ship v1.3 release", status="pending", priority=1)
            mem.add_conversation_summary("Discussed planning and tests")
            res = mem.semantic_search("python planning", limit=5)
            self.assertTrue(res.get("success"))
            self.assertGreaterEqual(len(res.get("results", [])), 1)


class TestGroundingV13(unittest.TestCase):
    def test_ranked_matches(self):
        grounder = ScreenGrounder()
        analysis = {
            "ui_elements": [
                {"type": "button", "label": "Search", "bounding_box": {"left": 10, "top": 10, "width": 100, "height": 20}},
                {"type": "button", "label": "Search docs", "bounding_box": {"left": 20, "top": 40, "width": 120, "height": 20}},
            ],
            "window_titles": [{"title": "Chrome", "bounding_box": {"left": 0, "top": 0, "width": 1280, "height": 800}}],
        }
        result = grounder.ground("search", analysis=analysis, active_window="Chrome")
        self.assertTrue(result.get("success"))
        self.assertIn("matches", result)
        self.assertGreaterEqual(len(result.get("matches", [])), 1)


if __name__ == "__main__":
    unittest.main()
