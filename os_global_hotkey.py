"""Global keyboard hotkeys wrapper on Windows using native ctypes APIs."""

import ctypes
import ctypes.wintypes
import threading
from logger import get_logger

_log = get_logger("os_global_hotkey")
user32 = ctypes.windll.user32

HOTKEY_ID = 101
MOD_CONTROL = 0x0002
VK_SPACE = 0x0020
WM_HOTKEY = 0x0312


class GlobalHotkeyListener:
    """Listens globally for Ctrl+Space shortcut and executes callback."""

    def __init__(self, callback):
        self.callback = callback
        self.thread = None
        self.running = False

    def start(self):
        """Start listening loop on a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        # Register hotkey on current background thread
        res = user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL, VK_SPACE)
        if not res:
            _log.error("Failed to register global hotkey Ctrl+Space. Key might be bound by another app.")
            return

        _log.info("Registered global hotkey Ctrl+Space successfully")
        msg = ctypes.wintypes.MSG()
        try:
            while self.running:
                # Blocks until a message is received
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0:
                    break
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    _log.info("Global hotkey event triggered")
                    self.callback()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            _log.error("Error in hotkey loop: %s", str(e))
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            _log.info("Unregistered global hotkey Ctrl+Space")

    def stop(self):
        """Unregister hotkey and signal loop thread to exit."""
        self.running = False
        if self.thread and self.thread.is_alive():
            # Send a dummy message to wake the thread out of GetMessageW blocking call
            user32.PostThreadMessageW(self.thread.ident, 0, 0, 0)
