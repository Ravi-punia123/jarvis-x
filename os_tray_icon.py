"""System tray icon integration for JARVIS using pystray."""

import threading
import os
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from os_startup_manager import set_startup, is_startup_enabled
from logger import get_logger

_log = get_logger("os_tray_icon")


class OSTrayIcon:
    """Manages the Windows system tray icon, menu actions, and toggle options."""

    def __init__(self, app):
        self.app = app
        self.icon = None
        self._tray_thread = None
        self._create_icon()

    def _create_icon_image(self):
        """Generate a beautiful neon-arc-reactor icon using Pillow."""
        # Try loading an existing file, otherwise generate a premium one
        icon_path = os.path.join("assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                return Image.open(icon_path)
            except Exception:
                pass

        # Generate a premium dark neon blue gradient/shape representing JARVIS
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # Background dark blue circle
        draw.ellipse([8, 8, 56, 56], fill=(10, 25, 47, 255), outline=(0, 242, 254, 255), width=2)
        # Inner neon blue ring
        draw.ellipse([18, 18, 46, 46], fill=(17, 34, 64, 255), outline=(0, 242, 254, 255), width=3)
        # Core glowing dot
        draw.ellipse([27, 27, 37, 37], fill=(0, 242, 254, 255))
        return image

    def _create_menu(self):
        """Create the system tray context menu."""
        def toggle_startup(icon, item):
            current = is_startup_enabled()
            set_startup(not current)

        menu = pystray.Menu(
            item("Open JARVIS", lambda: self.app.root.after(0, self._show_window)),
            item("Quick Launcher (Ctrl+Space)", lambda: self.app.root.after(0, self._show_launcher)),
            pystray.Menu.SEPARATOR,
            item("Daily Dashboard", lambda: self.app.root.after(0, self.app._show_daily_dashboard)),
            item("Dev Dashboard", lambda: self.app.root.after(0, self.app._show_dev_dashboard)),
            item("Settings", lambda: self.app.root.after(0, self.app._show_settings)),
            item("Start with Windows", toggle_startup, checked=lambda item: is_startup_enabled()),
            pystray.Menu.SEPARATOR,
            item("Exit", lambda: self.app.root.after(0, self._exit_app))
        )
        return menu

    def _exit_app(self):
        self.app._exit_requested = True
        self.app._on_close_attempt()

    def _create_icon(self):
        """Initialize the pystray Icon instance."""
        img = self._create_icon_image()
        self.icon = pystray.Icon("JARVIS", img, "JARVIS - Digital Chief of Staff", self._create_menu())

    def _show_window(self):
        """Restore main JARVIS UI window."""
        self.app.root.deiconify()
        self.app.root.lift()
        self.app.root.focus_force()

    def _show_launcher(self):
        """Open the floating launcher entry."""
        if hasattr(self.app, "floating_launcher"):
            self.app.floating_launcher.show()

    def start(self):
        """Start the system tray icon on a daemon background thread."""
        _log.info("Starting background tray icon thread")
        self._tray_thread = threading.Thread(target=self.icon.run, daemon=True)
        self._tray_thread.start()

    def stop(self):
        """Stop the tray icon process cleanly."""
        _log.info("Stopping system tray icon")
        if self.icon:
            self.icon.stop()
