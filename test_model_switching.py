import unittest
from unittest.mock import patch
from planner import Planner
from executor import Executor


class TestModelSwitching(unittest.TestCase):
    def test_planner_detects_switch_model_intent(self):
        planner = Planner()

        queries = [
            "switch to qwen3:8b",
            "use gemma4:12b",
            "change model to llama3",
            "use llama3",
            "select model qwen",
        ]

        for q in queries:
            plan = planner.plan(q)
            self.assertEqual(plan.get("action"), "switch_model", f"Failed for query: {q}")
            self.assertIn("model", plan.get("arguments", {}))

    def test_executor_switch_model_handling(self):
        ex = Executor()

        # Mock _verify_model_installed to return True
        with patch.object(ex, "_verify_model_installed", return_value=True):
            out = ex.execute({
                "action": "switch_model",
                "arguments": {"model": "qwen3:8b"}
            })
            self.assertTrue(out.get("success"))
            self.assertEqual(out.get("model"), "qwen3:8b")
            self.assertEqual(ex.settings.get("llm_model"), "qwen3:8b")

        # Mock _verify_model_installed to return False for missing model
        with patch.object(ex, "_verify_model_installed", return_value=False):
            out = ex.execute({
                "action": "switch_model",
                "arguments": {"model": "non-existent-model"}
            })
            self.assertFalse(out.get("success"))
            self.assertEqual(out.get("error"), "Model not installed.")


if __name__ == "__main__":
    unittest.main()
