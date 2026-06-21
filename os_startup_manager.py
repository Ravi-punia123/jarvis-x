"""Startup manager for JARVIS - configures run registry entry on Windows."""

import winreg
import sys
import os
from logger import get_logger

_log = get_logger("os_startup_manager")
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "JARVIS"


def set_startup(enabled: bool) -> bool:
    """Enable or disable startup with Windows."""
    try:
        # Determine path to executable or script
        if getattr(sys, "frozen", False):
            # Running as built executable
            exe_path = sys.executable
        else:
            # Running as script
            exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

        _log.info("Setting startup registry: enabled=%s, path=%s", enabled, exe_path)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        try:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            return True
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        _log.error("Failed to update startup registry: %s", str(e))
        return False


def is_startup_enabled() -> bool:
    """Check if JARVIS startup key is present."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False
