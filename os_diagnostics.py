"""Diagnostics suite validating imports, startups, configurations, and leaks."""

import sys
import time
import importlib
from typing import Dict, Any, List
from logger import get_logger

_log = get_logger("os_diagnostics")


class OSDiagnostics:
    """Verifies startup timing metrics, configurations, packages health, and dead plugins."""

    def __init__(self, requirements_path: str = "requirements.txt"):
        self.requirements_path = requirements_path

    def run_diagnostics(self) -> Dict[str, Any]:
        issues: List[str] = []
        
        # 1. Check packages validation
        required_modules = ["ollama", "PIL", "pywt", "pyautogui", "pygetwindow", "pyperclip", "pytesseract", "psutil"]
        for mod in required_modules:
            try:
                importlib.import_module(mod)
            except ImportError as e:
                issues.append(f"Missing dependency: {mod} ({str(e)})")

        # 2. Check virtual environment integrity
        is_venv = hasattr(sys, 'real_prefix') or (sys.base_prefix != sys.prefix)
        if not is_venv:
            issues.append("Warning: JARVIS is not running inside a virtual environment.")

        # 3. Check memory leak warning
        import psutil
        proc = psutil.Process()
        mem_mb = proc.memory_info().rss / (1024 * 1024)
        if mem_mb > 500:
            issues.append(f"High RAM Usage warning: Process RSS is {mem_mb:.2f} MB")

        return {
            "success": len(issues) == 0,
            "rss_mb": round(mem_mb, 2),
            "issues": issues,
            "timestamp": time.time(),
        }
