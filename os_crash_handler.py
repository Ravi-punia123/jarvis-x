"""Unhandled exception crash handler and logger for JARVIS."""

import sys
import traceback
import tkinter as tk
from tkinter import messagebox
from logger import get_logger

_log = get_logger("os_crash_handler")


def handle_exception(exc_type, exc_value, exc_traceback):
    """Callback for sys.excepthook to handle global crashes."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    _log.critical("Unhandled critical crash: %s", tb_msg)

    # Write local crash file
    try:
        with open("crash_report.log", "w", encoding="utf-8") as f:
            f.write(tb_msg)
    except Exception as e:
        _log.error("Failed to write crash_report.log: %s", str(e))

    # Try showing a Tkinter alert message box safely
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "JARVIS Critical Error",
            f"JARVIS encountered a critical system error:\n\n"
            f"{exc_value}\n\n"
            f"Diagnostic details have been saved to 'crash_report.log'. "
            f"The application will now shut down. Please restart to recover.",
        )
        root.destroy()
    except Exception:
        pass

    sys.exit(1)


def register_crash_handler():
    """Register the global hook in the interpreter environment."""
    sys.excepthook = handle_exception
    _log.info("Registered global system exception hook")
