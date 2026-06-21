"""Floating quick launcher and desktop notifications system for JARVIS."""

import tkinter as tk
import threading
from ui_theme import BG_SECONDARY, BG_TERTIARY, BG_ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, PADDING_MEDIUM
from logger import get_logger

_log = get_logger("os_floating_launcher")


class FloatingLauncher:
    """A floating, Spotlight-like input bar triggered globally by Ctrl+Space."""

    def __init__(self, app):
        self.app = app
        self.win = None

    def show(self):
        """Toggle launcher window visibility."""
        if self.win and self.win.winfo_exists():
            self.hide()
            return

        _log.info("Displaying floating quick launcher")
        self.win = tk.Toplevel(self.app.root)
        self.win.overrideredirect(True)  # Borderless
        self.win.attributes("-topmost", True)
        self.win.configure(bg=BG_SECONDARY)

        # Center on screen
        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()
        w, h = 520, 60
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")

        # Decorative neon border
        border = tk.Frame(self.win, bg=BG_ACCENT, bd=1)
        border.pack(fill="both", expand=True)

        inner = tk.Frame(border, bg=BG_SECONDARY)
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        # Entry text input
        self.entry = tk.Entry(
            inner,
            bg=BG_TERTIARY,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            font=("Consolas", 12),
            relief="flat",
            bd=0,
        )
        self.entry.pack(fill="x", padx=PADDING_MEDIUM, pady=16)
        self.entry.focus_set()

        # Keyboard bindings
        self.entry.bind("<Return>", self._on_submit)
        self.entry.bind("<Escape>", lambda e: self.hide())
        self.win.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_out(self, event):
        # Delay check to ensure focus didn't move inside child components
        self.win.after(100, self._check_focus_and_hide)

    def _check_focus_and_hide(self):
        if self.win and self.win.winfo_exists():
            focus = self.win.focus_get()
            if not focus or focus.winfo_toplevel() != self.win:
                self.hide()

    def hide(self):
        """Hide quick launcher window."""
        if self.win:
            try:
                self.win.destroy()
            except Exception:
                pass
            self.win = None

    def _on_submit(self, event=None):
        query = self.entry.get().strip()
        self.hide()
        if not query:
            return

        # Show initial feedback toast
        self.show_toast("JARVIS Quick Action", f"Processing command: {query}")

        # Run query execution pipeline in background thread
        threading.Thread(target=self._run_query, args=(query,), daemon=True).start()

    def _run_query(self, query):
        try:
            self.app.memory.add_user_message(query)
            self.app.history_manager.add_message("user", query)

            # Plan and execute
            plan = self.app.planner.plan(query)
            response = ""
            if isinstance(plan, dict) and plan.get("action") == "chat":
                # Chat query stream
                for chunk in self.app.ai.stream_response(query, self.app.memory):
                    response += chunk
            else:
                # Tools execution
                result = self.app.executor.execute(plan)
                summary_input = f"System execute actions outcome: {result}. Summarize accomplishments clearly for the user."
                for chunk in self.app.ai.stream_response(summary_input, self.app.memory):
                    response += chunk

            # Update memory history
            self.app.memory.add_assistant_message(response)
            self.app.history_manager.add_message("assistant", response)

            # Display response toast notification
            self.show_toast("JARVIS Execution Complete", response)

            # If main GUI chat is currently visible, update it too
            if self.app.root.winfo_viewable():
                self.app.root.after(0, lambda: self.app._append_user_message(query))
                self.app.root.after(0, lambda: self.app._append_assistant_message(response))
        except Exception as e:
            _log.error("Quick action execution error: %s", str(e))
            self.show_toast("JARVIS Error", f"Command failed: {e}")

    def show_toast(self, title, message):
        """Display a desktop overlay toast notification on the UI thread."""
        self.app.root.after(0, lambda: self._show_toast_ui(title, message))

    def _show_toast_ui(self, title, message):
        toast = tk.Toplevel(self.app.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=BG_SECONDARY)

        # Position toast in bottom-right corner of desktop
        screen_w = toast.winfo_screenwidth()
        screen_h = toast.winfo_screenheight()
        w, h = 340, 110
        x = screen_w - w - 24
        y = screen_h - h - 60
        toast.geometry(f"{w}x{h}+{x}+{y}")

        # Accent border
        b = tk.Frame(toast, bg=BG_ACCENT, bd=1)
        b.pack(fill="both", expand=True)

        inner = tk.Frame(b, bg=BG_SECONDARY)
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        # Header Title
        tk.Label(
            inner,
            text=title,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
            font=("Consolas", 10, "bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=6)

        # Notification message
        msg_text = message[:140] + ("..." if len(message) > 140 else "")
        tk.Label(
            inner,
            text=msg_text,
            bg=BG_SECONDARY,
            fg=TEXT_SECONDARY,
            font=("Consolas", 9),
            anchor="nw",
            justify="left",
            wrap=300,
        ).pack(fill="both", expand=True, padx=12, pady=(0, 6))

        # Auto-destruct overlay toast after 5 seconds
        toast.after(5000, toast.destroy)
