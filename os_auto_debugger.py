"""Auto Debugger capturing tracebacks, diagnosing causes, and attempting recovery."""

import traceback
from typing import Dict, Any, Optional
from logger import get_logger

_log = get_logger("os_debugger")


class OSAutoDebugger:
    """Evaluates exceptions, correlates log states, and attempts auto-recovery steps."""

    def __init__(self):
        pass

    def debug_exception(self, exc: Exception, context_info: Optional[str] = None) -> Dict[str, Any]:
        tb_str = traceback.format_exc()
        exc_name = type(exc).__name__
        exc_msg = str(exc)

        # 1. Map to probable root cause
        probable_cause = "Unknown error"
        suggested_action = "Inspect the logs and traceback details"
        recovery_attempted = False
        recovery_success = False

        if exc_name == "ConnectionError" or "Ollama" in exc_msg or "offline" in exc_msg.lower():
            probable_cause = "Local Ollama server is offline or unreachable."
            suggested_action = "Make sure Ollama is launched (ollama serve) and running."
        elif exc_name == "ImportError" or exc_name == "ModuleNotFoundError":
            import sys
            import subprocess
            missing_module = exc_msg.replace("No module named ", "").strip().strip("'").strip('"')
            probable_cause = f"Dependency package '{missing_module}' is missing."
            suggested_action = f"Running: pip install {missing_module}"
            recovery_attempted = True
            try:
                _log.info("Auto Debugger attempting recovery: installing missing package '%s'...", missing_module)
                subprocess.run([sys.executable, "-m", "pip", "install", missing_module], check=True, capture_output=True)
                recovery_success = True
                _log.info("Recovery successful: Installed missing package '%s'.", missing_module)
            except Exception as e:
                recovery_success = False
                _log.error("Recovery failed: unable to install package: %s", str(e))
        elif exc_name == "UnicodeEncodeError" or exc_name == "UnicodeDecodeError":
            probable_cause = "Console attempt encoding mapping conflict."
            suggested_action = "Verify input encoding is set to UTF-8."

        _log.error("Exception Debugger Captured: %s: %s\n%s", exc_name, exc_msg, tb_str)

        return {
            "exception_type": exc_name,
            "exception_message": exc_msg,
            "traceback": tb_str,
            "probable_cause": probable_cause,
            "suggested_action": suggested_action,
            "recovery_attempted": recovery_attempted,
            "recovery_success": recovery_success,
        }
