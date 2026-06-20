"""Modern AI desktop assistant UI - Main application window."""

import threading
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import simpledialog
from datetime import datetime
from typing import Optional
import traceback
import os
import json
from pathlib import Path

from ai import OllamaAssistant
from config import (
    APP_TITLE,
    STATUS_LISTENING,
    STATUS_READY,
    STATUS_THINKING,
    STATUS_TYPING,
)
from executor import Executor
from memory import MemoryManager
from planner import Planner
from speech import SpeechManager
from vision import VisionManager

from ui_theme import *
from ui_components import RoundedButton, LoadingIndicator, MessageBubble, StatusIndicator
from ui_file_manager import FileManager
from ui_history import HistoryManager
from input_router import InputRouter
from settings_manager import SettingsManager
from task_queue import TaskQueue
from logger import get_logger

try:
    from tkinterdnd2 import DND_FILES, DND_TEXT
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False


class JarvisApp:
    """Modern dark-themed JARVIS desktop assistant with multimodal input."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_DEFAULT_WIDTH}x{WINDOW_DEFAULT_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(bg=BG_PRIMARY)

        # Backends
        self.ai = OllamaAssistant()
        self.memory = MemoryManager()
        self.planner = Planner()
        self.executor = Executor()
        self.executor.autonomous_loop.planner = self.planner
        self.vision = VisionManager()
        self.speech = SpeechManager()
        self.file_manager = FileManager()
        self.history_manager = HistoryManager()
        self.settings_manager = SettingsManager()
        self.task_queue = TaskQueue()
        self.task_queue.register_callback("ui", self._on_task_event)
        self.log = get_logger("ui")

        # UI state
        self.status_var = tk.StringVar(value=STATUS_READY)
        self.model_status_var = tk.StringVar(value=f"Model: {self.ai.model_name}")
        self.inference_var = tk.StringVar(value="Inference: idle")
        self.execution_var = tk.StringVar(value="Execution: idle")
        self.is_generating = False
        self._streaming = False
        self._assistant_buffer = ""
        self.cancel_requested = False
        self.selected_session_id: Optional[int] = None
        self.current_task_id: Optional[str] = None
        self.execution_panel_expanded = False
        self.settings = self.settings_manager.all()
        self.ai.configure(
            model_name=self.settings.get("llm_model"),
            temperature=self.settings.get("temperature"),
            context_length=self.settings.get("context_length"),
        )
        self.vision.set_model(self.settings.get("vision_model", "auto"))
        self.vision.set_timeout(int(self.settings.get("timeout_seconds", 600)))

        # Build UI
        self._build_ui()
        self._bind_shortcuts()
        self.history_manager.new_session()
        
        # Async Ollama health check
        threading.Thread(target=self._check_ollama_health, daemon=True).start()

        # JARVIS v2.0 Background OS Services
        from os_observer_service import ContinuousObserver
        from os_notification_center import OSNotificationCenter
        from os_coordinator_agent import CoordinatorAgent
        from os_voice_listener import VoiceWakeListener
        from os_plugin_registry import DynamicPluginRegistry
        from os_workflow_engine import WorkflowEngine

        self.notification_center = OSNotificationCenter()
        self.notification_center.register_listener(self._on_task_event)

        self.continuous_observer = ContinuousObserver(self.memory)
        self.continuous_observer.start()

        self.coordinator = CoordinatorAgent(self.planner, self.executor)
        self.plugins = DynamicPluginRegistry()
        self.workflows = WorkflowEngine(self.executor)

        # Trigger recording when wake word is spoken
        def voice_trigger(phrase):
            self.root.after(0, lambda: self._append_user_message(f"[Wake trigger: {phrase}]"))
            self.root.after(0, self._on_voice)

        self.voice_listener = VoiceWakeListener(self.speech, voice_trigger)
        self.voice_listener.start()

        # Handle window minimized minimize-to-tray mapping gracefully
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        # JARVIS v3.0 Self-Improving Platform Modules
        from os_health_manager import OSHealthManager
        from os_diagnostics import OSDiagnostics
        from os_benchmark_suite import OSBenchmarkSuite
        from os_auto_debugger import OSAutoDebugger
        from os_learning_engine import OSLearningEngine

        self.health_manager = OSHealthManager()
        self.diagnostics = OSDiagnostics()
        self.benchmarks = OSBenchmarkSuite()
        self.debugger = OSAutoDebugger()
        self.learning_engine = OSLearningEngine()

        # Track startup metric benchmark
        self.benchmarks.record("startup_latency", time.time() - self.root.winfo_toplevel().tk.call("clock", "clicks"))

    def _on_task_event(self, event_name: str, payload: dict):
        """Handle task queue events on the UI thread."""
        def apply_event():
            if event_name == "queued":
                self.execution_var.set("Execution: queued")
                self._update_execution_log(f"[queue] queued {payload.get('label', '')}")
            elif event_name == "started":
                self.execution_var.set("Execution: running")
                self._update_execution_log(f"[queue] started {payload.get('label', '')}")
            elif event_name == "completed":
                self.execution_var.set("Execution: completed")
            elif event_name == "failed":
                self.execution_var.set("Execution: failed")
                self._show_toast(f"Task failed: {payload.get('error', 'Unknown error')}", "error")
            elif event_name == "cancelled":
                self.execution_var.set("Execution: cancelled")

        self.root.after(0, apply_event)

    def _bind_shortcuts(self):
        """Bind global keyboard shortcuts."""
        self.root.bind("<Control-Return>", self._on_send)
        self.root.bind("<Control-l>", self._clear_chat)
        self.root.bind("<Control-L>", self._clear_chat)
        self.root.bind("<Control-Shift-S>", lambda e: self._on_screenshot())
        self.root.bind("<Control-o>", lambda e: self._on_upload())
        self.root.bind("<Control-O>", lambda e: self._on_upload())
        self.root.bind("<Escape>", self._on_cancel_current)

    def _build_ui(self):
        """Build the complete modern UI layout."""
        # Main container with sidebar
        main_frame = tk.Frame(self.root, bg=BG_PRIMARY)
        main_frame.pack(fill="both", expand=True)

        # =====================================================================
        # SIDEBAR
        # =====================================================================
        sidebar = self._build_sidebar(main_frame)
        sidebar.pack(side="left", fill="both", padx=0, pady=0)

        # =====================================================================
        # MAIN CONTENT AREA
        # =====================================================================
        content_frame = tk.Frame(main_frame, bg=BG_PRIMARY)
        content_frame.pack(side="right", fill="both", expand=True)

        # Header with model info
        header = self._build_header(content_frame)
        header.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        # Chat area
        chat_container = tk.Frame(content_frame, bg=BG_PRIMARY)
        chat_container.pack(fill="both", expand=True, padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM))

        self.chat_canvas = tk.Canvas(
            chat_container,
            bg=BG_SECONDARY,
            highlightthickness=0,
            bd=0,
        )
        self.chat_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(chat_container, command=self.chat_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.chat_canvas.config(yscrollcommand=scrollbar.set)

        self.chat_frame = tk.Frame(self.chat_canvas, bg=BG_SECONDARY)
        self.chat_window = self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")

        def on_chat_frame_configure(event):
            self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
            if self.chat_frame.winfo_reqheight() > self.chat_canvas.winfo_height():
                self.chat_canvas.yview_moveto(1)

        self.chat_frame.bind("<Configure>", on_chat_frame_configure)

        # Input area
        input_area = self._build_input_area(content_frame)
        input_area.pack(fill="x", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 0))

        # Attachment strip
        attachments = self._build_attachment_panel(content_frame)
        attachments.pack(fill="x", padx=PADDING_MEDIUM, pady=(PADDING_SMALL, 0))

        # Execution panel
        execution_panel = self._build_execution_panel(content_frame)
        execution_panel.pack(fill="x", padx=PADDING_MEDIUM, pady=(PADDING_SMALL, 0))

        # Status bar
        status_bar = self._build_status_bar(content_frame)
        status_bar.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)

    def _build_sidebar(self, parent):
        """Build the left sidebar with history and controls."""
        sidebar = tk.Frame(parent, bg=BG_SECONDARY, width=SIDEBAR_WIDTH)
        sidebar.pack_propagate(False)

        # Title
        title = tk.Label(
            sidebar,
            text="JARVIS",
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
            font=FONT_TITLE,
        )
        title.pack(pady=PADDING_MEDIUM, padx=PADDING_MEDIUM)

        # New chat button
        new_btn = RoundedButton(
            sidebar,
            text="+ New Chat",
            command=self._new_chat,
            width=SIDEBAR_WIDTH - 20,
            height=BUTTON_HEIGHT,
            bg=BG_ACCENT,
        )
        new_btn.pack(pady=PADDING_NORMAL, padx=PADDING_MEDIUM)

        # Separator
        sep = tk.Frame(sidebar, bg=SEPARATOR_COLOR, height=1)
        sep.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_NORMAL)

        # History label
        hist_label = tk.Label(
            sidebar,
            text="Chat History",
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
            font=FONT_SMALL_BOLD,
        )
        hist_label.pack(anchor="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, PADDING_SMALL))

        self.history_search_var = tk.StringVar()
        history_search = tk.Entry(
            sidebar,
            textvariable=self.history_search_var,
            bg=BG_TERTIARY,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            font=FONT_SMALL,
        )
        history_search.pack(fill="x", padx=PADDING_MEDIUM, pady=(0, PADDING_SMALL))
        history_search.bind("<KeyRelease>", lambda e: self._update_history_list())

        # History list (scrollable)
        hist_frame = tk.Frame(sidebar, bg=BG_SECONDARY)
        hist_frame.pack(fill="both", expand=True, padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        self.history_canvas = tk.Canvas(
            hist_frame,
            bg=BG_SECONDARY,
            highlightthickness=0,
            bd=0,
        )
        self.history_canvas.pack(side="left", fill="both", expand=True)

        hist_scrollbar = ttk.Scrollbar(hist_frame, command=self.history_canvas.yview)
        hist_scrollbar.pack(side="right", fill="y")
        self.history_canvas.config(yscrollcommand=hist_scrollbar.set)

        self.history_list_frame = tk.Frame(self.history_canvas, bg=BG_SECONDARY)
        self.history_window = self.history_canvas.create_window((0, 0), window=self.history_list_frame, anchor="nw")

        def on_hist_frame_configure(event):
            self.history_canvas.configure(scrollregion=self.history_canvas.bbox("all"))

        self.history_list_frame.bind("<Configure>", on_hist_frame_configure)
        self._update_history_list()

        # Bottom separator
        bottom_sep = tk.Frame(sidebar, bg=SEPARATOR_COLOR, height=1)
        bottom_sep.pack(fill="x", side="bottom", padx=PADDING_MEDIUM, pady=PADDING_NORMAL)

        # Settings button
        settings_btn = RoundedButton(
            sidebar,
            text="⚙️ Settings",
            command=self._show_settings,
            width=SIDEBAR_WIDTH - 20,
            height=BUTTON_HEIGHT,
            bg=BG_TERTIARY,
            hover_bg=BG_ACCENT,
        )
        settings_btn.pack(side="bottom", pady=PADDING_MEDIUM, padx=PADDING_MEDIUM)

        memory_btn = RoundedButton(
            sidebar,
            text="Memory",
            command=self._show_memory_panel,
            width=SIDEBAR_WIDTH - 20,
            height=BUTTON_HEIGHT,
            bg=BG_TERTIARY,
            hover_bg=BG_ACCENT,
        )
        memory_btn.pack(side="bottom", pady=(0, PADDING_SMALL), padx=PADDING_MEDIUM)

        dev_dashboard_btn = RoundedButton(
            sidebar,
            text="🛠️ Dev Dashboard",
            command=self._show_dev_dashboard,
            width=SIDEBAR_WIDTH - 20,
            height=BUTTON_HEIGHT,
            bg=BG_TERTIARY,
            hover_bg=BG_ACCENT,
        )
        dev_dashboard_btn.pack(side="bottom", pady=(0, PADDING_SMALL), padx=PADDING_MEDIUM)

        return sidebar

    def _build_header(self, parent):
        """Build the header with a professional health diagnostic dashboard."""
        header = tk.Frame(parent, bg=BG_SECONDARY, height=STATUS_BAR_HEIGHT)
        header.pack_propagate(False)

        # Left: Model indicator
        self.model_status_label = tk.Label(
            header,
            textvariable=self.model_status_var,
            bg=BG_SECONDARY,
            fg=TEXT_SECONDARY,
            font=FONT_SMALL_BOLD,
        )
        self.model_status_label.pack(side="left", padx=PADDING_NORMAL)

        # Vertical separator
        tk.Frame(header, bg=SEPARATOR_COLOR, width=1).pack(side="left", fill="y", padx=PADDING_NORMAL, pady=PADDING_SMALL)

        # Health statuses
        self.ollama_health_label = tk.Label(header, text="⚫ Ollama", bg=BG_SECONDARY, fg=TEXT_MUTED, font=FONT_TINY)
        self.ollama_health_label.pack(side="left", padx=PADDING_NORMAL)

        self.vision_health_label = tk.Label(header, text="🟢 Vision", bg=BG_SECONDARY, fg=STATUS_SUCCESS, font=FONT_TINY)
        self.vision_health_label.pack(side="left", padx=PADDING_NORMAL)

        self.memory_health_label = tk.Label(header, text="🟢 Memory", bg=BG_SECONDARY, fg=STATUS_SUCCESS, font=FONT_TINY)
        self.memory_health_label.pack(side="left", padx=PADDING_NORMAL)

        self.skills_health_label = tk.Label(header, text="🟢 Skills", bg=BG_SECONDARY, fg=STATUS_SUCCESS, font=FONT_TINY)
        self.skills_health_label.pack(side="left", padx=PADDING_NORMAL)

        self.voice_health_label = tk.Label(header, text="⚫ Voice", bg=BG_SECONDARY, fg=TEXT_MUTED, font=FONT_TINY)
        self.voice_health_label.pack(side="left", padx=PADDING_NORMAL)

        # Right: Inference status
        infer_label = tk.Label(
            header,
            textvariable=self.inference_var,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
            font=FONT_SMALL,
        )
        infer_label.pack(side="right", padx=PADDING_NORMAL)

        # Periodically refresh health status dashboard
        self.root.after(1000, self._refresh_health_dashboard)

        return header

    def _refresh_health_dashboard(self):
        """Update system health statuses dynamically."""
        try:
            # Check Ollama online status
            if self.ai.is_online():
                self.ollama_health_label.config(text="🟢 Ollama", fg=STATUS_SUCCESS)
            else:
                self.ollama_health_label.config(text="🔴 Ollama", fg=STATUS_ERROR)

            # Check Voice module (PyAudio check)
            try:
                try:
                    import pyaudio
                except ImportError:
                    import pyaudiowpatch as pyaudio
                self.voice_health_label.config(text="🟢 Voice", fg=STATUS_SUCCESS)
            except ImportError:
                self.voice_health_label.config(text="⚫ Voice", fg=TEXT_MUTED)

            # Keep model name accurate
            self.model_status_var.set(f"Model: {self.ai.model_name}")
        except Exception:
            pass
        # Schedule next check in 10 seconds
        self.root.after(10000, self._refresh_health_dashboard)

    def _build_input_area(self, parent):
        """Build the multimodal input area."""
        input_frame = tk.Frame(parent, bg=BG_SECONDARY)

        # Text input with frame for styling
        input_inner = tk.Frame(input_frame, bg=BG_SECONDARY)
        input_inner.pack(fill="both", expand=True, padx=0, pady=0)

        self.input_box = tk.Text(
            input_inner,
            height=3,
            wrap="word",
            font=FONT_BODY,
            bg=BG_TERTIARY,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            padx=PADDING_NORMAL,
            pady=PADDING_NORMAL,
        )
        self.input_box.pack(fill="both", expand=True)

        def _handle_enter(event):
            # Shift key check
            if event.state & 0x0001:  # Shift held down
                return None  # Let default behavior happen (insert newline)
            self._on_send()
            return "break"  # Stop enter character insertion

        self.input_box.bind("<Return>", _handle_enter)
        self.input_box.bind("<Control-v>", self._on_paste_clipboard)
        
        # Support drag & drop if available
        if DRAG_DROP_AVAILABLE:
            try:
                self.input_box.drop_target_register(DND_FILES, DND_TEXT)
                self.input_box.dnd_bind('<<Drop>>', self._on_drop_files)
            except Exception as e:
                pass  # Drag-drop not critical

        # Button row
        button_frame = tk.Frame(input_frame, bg=BG_SECONDARY)
        button_frame.pack(fill="x", padx=0, pady=PADDING_SMALL)

        # File upload button
        upload_btn = RoundedButton(
            button_frame,
            text="📎 Add File",
            command=self._on_upload,
            width=100,
            height=32,
            bg=BG_TERTIARY,
            hover_bg=BG_ACCENT,
        )
        upload_btn.pack(side="left", padx=(0, PADDING_SMALL))

        # Screenshot button
        screen_btn = RoundedButton(
            button_frame,
            text="📸 Screenshot",
            command=self._on_screenshot,
            width=100,
            height=32,
            bg=BG_TERTIARY,
            hover_bg=BG_ACCENT,
        )
        screen_btn.pack(side="left", padx=PADDING_SMALL)

        # Voice button
        self.voice_btn = RoundedButton(
            button_frame,
            text="🎤 Voice",
            command=self._on_voice,
            width=100,
            height=32,
            bg=BG_TERTIARY,
            hover_bg=BG_ACCENT,
        )
        self.voice_btn.pack(side="left", padx=PADDING_SMALL)

        # Send button
        self.send_btn = RoundedButton(
            button_frame,
            text="Send",
            command=self._on_send,
            width=100,
            height=32,
            bg=BG_ACCENT,
            hover_bg=BUTTON_HOVER,
        )
        self.send_btn.pack(side="right", padx=0)

        return input_frame

    def _build_status_bar(self, parent):
        """Build the status bar at the bottom."""
        status_frame = tk.Frame(parent, bg=BG_SECONDARY, height=STATUS_BAR_HEIGHT)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg=BG_SECONDARY,
            fg=TEXT_SECONDARY,
            font=FONT_SMALL,
            anchor="w",
        )
        self.status_label.pack(side="left", padx=PADDING_NORMAL, fill="both", expand=True)

        exec_label = tk.Label(
            status_frame,
            textvariable=self.execution_var,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
            font=FONT_SMALL,
            anchor="e",
        )
        exec_label.pack(side="right", padx=PADDING_NORMAL)

        return status_frame

    def _build_attachment_panel(self, parent):
        """Show current attached files with quick remove actions."""
        panel = tk.Frame(parent, bg=BG_SECONDARY)
        self.attachments_frame = panel
        self._refresh_attachments_ui()
        return panel

    def _build_execution_panel(self, parent):
        """Build a compact panel for pipeline/activity updates."""
        panel = tk.Frame(parent, bg=BG_SECONDARY)
        header_row = tk.Frame(panel, bg=BG_SECONDARY)
        header_row.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_SMALL, 0))

        title = tk.Label(
            header_row,
            text="Execution",
            bg=BG_SECONDARY,
            fg=TEXT_SECONDARY,
            font=FONT_SMALL,
            anchor="w",
        )
        title.pack(side="left")

        self.execution_toggle_btn = RoundedButton(
            header_row,
            text="Show",
            command=self._toggle_execution_panel,
            width=70,
            height=26,
            bg=BG_TERTIARY,
            hover_bg=BG_ACCENT,
        )
        self.execution_toggle_btn.pack(side="right")

        self.execution_progress = ttk.Progressbar(panel, mode="determinate", maximum=100)
        self.execution_progress.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_SMALL, 0))

        self.execution_text = tk.Text(
            panel,
            height=3,
            wrap="word",
            bg=BG_TERTIARY,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=FONT_SMALL,
            padx=PADDING_NORMAL,
            pady=PADDING_SMALL,
        )
        # Omit packing self.execution_text so it starts collapsed
        self.execution_text.insert("1.0", "Waiting for next request...")
        self.execution_text.config(state="disabled")

        action_row = tk.Frame(panel, bg=BG_SECONDARY)
        action_row.pack(fill="x", padx=PADDING_NORMAL, pady=(0, PADDING_SMALL))
        RoundedButton(
            action_row,
            text="Cancel",
            command=self._on_cancel_current,
            width=90,
            height=30,
            bg=BG_TERTIARY,
            hover_bg=STATUS_ERROR,
        ).pack(side="left")
        RoundedButton(
            action_row,
            text="Retry",
            command=self._retry_last_task,
            width=90,
            height=30,
            bg=BG_TERTIARY,
            hover_bg=BG_ACCENT,
        ).pack(side="left", padx=(PADDING_SMALL, 0))

        return panel

    def _toggle_execution_panel(self):
        self.execution_panel_expanded = not self.execution_panel_expanded
        if self.execution_panel_expanded:
            self.execution_text.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_SMALL)
            self.execution_toggle_btn.configure(text="Hide")
        else:
            self.execution_text.pack_forget()
            self.execution_toggle_btn.configure(text="Show")

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _on_send(self, event=None):
        """Send message from input box."""
        if self.is_generating:
            return

        attached_files = self.file_manager.list_files()
        text = self.input_box.get("1.0", "end").strip()
        if not text and not attached_files:
            return

        # Include attached files in context if any
        if attached_files:
            file_list = "\n".join(
                [
                    f"- {f.get('name', 'file')} ({InputRouter.get_file_description(f.get('path') or f.get('name', ''))})"
                    for f in attached_files
                ]
            )
            full_message = f"{text}\n\n[Attached files]:\n{file_list}"
            
            # Log routing context
            routing_paths = [f.get("path") or f.get("name", "") for f in attached_files]
            context = InputRouter.analyze_request_context(text, routing_paths)
            if context.get('needs_multimodal'):
                self.status_var.set(f"📊 Multimodal input detected ({context['file_count']} files)")
        else:
            full_message = text

        display_text = text or "[Sent attachments]"
        self.memory.add_user_message(display_text)
        self.history_manager.add_message("user", display_text)
        self._append_user_message(display_text)
        self.input_box.delete("1.0", "end")
        self.input_box.config(state="disabled")
        self.send_btn.config(state="disabled")
        self.voice_btn.config(state="disabled")
        self.is_generating = True
        self.status_var.set(STATUS_TYPING)

        files_snapshot = [dict(item) for item in attached_files]
        self.current_task_id = self.task_queue.submit(
            "process_request",
            lambda: self._process_request(full_message, files_snapshot),
        )

    def _on_upload(self):
        """Open file dialog for upload."""
        files = filedialog.askopenfilenames(
            title="Add files",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.webp"),
                ("Documents", "*.pdf *.docx *.txt *.md *.csv *.xlsx"),
                ("Code", "*.py *.js *.html *.css *.json"),
                ("All", "*.*"),
            ],
        )
        for file in files:
            success, msg = self.file_manager.add_file(file)
            self.status_var.set(msg)
        self._refresh_attachments_ui()

    def _on_screenshot(self):
        """Capture and analyze screen."""
        if self.is_generating:
            return
        self.is_generating = True
        self.status_var.set("📸 Capturing screenshot...")
        self.execution_var.set("Execution: vision capture")
        self._update_execution_log("[vision] Capturing screenshot")
        self.send_btn.config(state="disabled")
        threading.Thread(target=self._process_screenshot, daemon=True).start()

    def _process_screenshot(self):
        """Process screen capture in background."""
        try:
            cap = self.vision.capture()
            if cap.get("success"):
                capture_elapsed = cap.get("elapsed_capture_seconds")
                if capture_elapsed is not None:
                    self._update_execution_log(f"[vision] Capture complete in {capture_elapsed:.2f}s")
                self._append_user_message("[Screenshot captured]")
                self.status_var.set("Analyzing screenshot...")
                self.inference_var.set("Inference: vision running")
                self._update_execution_log("[vision] Running screen analysis")
                result = self.vision.analyze(cap.get("path", ""))
                self.root.after(0, self._finish_vision, result)
            else:
                self.root.after(0, lambda: self.status_var.set(f"Screenshot failed: {cap.get('error')}"))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
        finally:
            self.is_generating = False
            self.root.after(0, lambda: self.send_btn.config(state="normal"))

    def _finish_vision(self, result):
        """Display vision analysis result."""
        if result.get("success"):
            message = result.get("message", "Analysis complete")
            self._append_assistant_message(message)
            self.memory.add_assistant_message(message)
            elapsed = result.get("elapsed_inference_seconds")
            if elapsed is not None:
                self.inference_var.set(f"Inference: {elapsed:.1f}s")
        else:
            error = result.get("error", "Unknown error")
            self._append_assistant_message(f"❌ Vision error: {error}")
            self.memory.add_assistant_message(f"Vision error: {error}")
            self.inference_var.set("Inference: vision failed")
        self.is_generating = False
        self.execution_var.set("Execution: idle")
        self.status_var.set(STATUS_READY)

    def _on_voice(self):
        """Start voice input."""
        if self.is_generating:
            return
        self.status_var.set(STATUS_LISTENING)
        self.voice_btn.config(state="disabled")
        self.send_btn.config(state="disabled")
        threading.Thread(target=self._process_voice, daemon=True).start()

    def _process_voice(self):
        """Process voice input in background."""
        try:
            text = self.speech.listen()
            if text:
                self.root.after(0, lambda: self.input_box.delete("1.0", "end"))
                self.root.after(0, lambda: self.input_box.insert("1.0", text))
                self.root.after(0, lambda: self.status_var.set(STATUS_READY))
                self.root.after(0, lambda: self.voice_btn.config(state="normal"))
                self.root.after(0, lambda: self.send_btn.config(state="normal"))
            else:
                self.root.after(0, lambda: self.status_var.set("No speech detected"))
                self.root.after(0, lambda: self.voice_btn.config(state="normal"))
                self.root.after(0, lambda: self.send_btn.config(state="normal"))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Voice error: {e}"))
            self.root.after(0, lambda: self.voice_btn.config(state="normal"))
            self.root.after(0, lambda: self.send_btn.config(state="normal"))

    def _process_request(self, prompt: str, attached_files=None):
        """Process user request in background thread."""
        try:
            self.log.info("processing request='%s'", prompt[:160])
            attached_files = attached_files or []
            self.planner.set_observer_state(self.executor.observer.get_latest_state())
            self.root.after(0, lambda: self.execution_var.set("Execution: planning"))
            self.root.after(0, lambda: self._update_execution_log("[planner] Building action plan"))

            # Fast path: uploaded image analysis through vision model.
            image_paths = [
                f.get("path") for f in attached_files
                if isinstance(f, dict) and f.get("type") == "image" and f.get("path")
            ]
            if image_paths:
                self.root.after(0, lambda: self.execution_var.set("Execution: image analysis"))
                self.root.after(0, lambda: self.inference_var.set("Inference: vision running"))
                self.root.after(0, lambda: self._update_execution_log(f"[vision] analyzing {len(image_paths)} uploaded image(s)"))
                summaries = []
                for image_path in image_paths:
                    result = self.vision.analyze_image(image_path, context="uploaded image")
                    if result.get("success"):
                        summaries.append(result.get("message", "{}"))
                    else:
                        summaries.append(f"Vision error: {result.get('error', 'unknown error')}")

                combined = "\n\n".join(summaries)
                self.root.after(0, lambda m=combined: self._append_assistant_message(m))
                self.root.after(0, lambda m=combined: self.memory.add_assistant_message(m))
                self.root.after(0, self._finish_request)
                return

            plan = self.planner.plan(prompt)

            if isinstance(plan, dict) and plan.get("action") == "chat":
                self.root.after(0, lambda: self.status_var.set(STATUS_THINKING))
                self.root.after(0, lambda: self.execution_var.set("Execution: chat"))
                self.root.after(0, lambda: self._update_execution_log("[chat] Streaming model response"))
                self._streaming = True
                self.cancel_requested = False
                try:
                    for chunk in self.ai.stream_response(prompt, self.memory):
                        if self.cancel_requested:
                            break
                        self.root.after(0, self._handle_stream_chunk, chunk)
                    self.root.after(0, self._finish_stream)
                except Exception as e:
                    self.root.after(
                        0,
                        lambda: self._show_exception(e, "ai", "stream_response"),
                    )
                    self.root.after(0, self._finish_stream)
            else:
                self.root.after(0, lambda: self.status_var.set("Executing..."))
                self.root.after(0, lambda: self.execution_var.set("Execution: tools"))
                self.root.after(0, lambda: self._update_execution_log("[executor] Running tool pipeline"))

                result = None
                for event in self.executor.stream_execute(plan):
                    if not isinstance(event, dict):
                        continue
                    message = event.get("message", "")
                    if message:
                        self.root.after(0, lambda m=message: self._update_execution_log(m))
                    if event.get("event") == "step_start":
                        self.root.after(0, lambda s=event.get("step", 0): self.execution_var.set(f"Execution: step {s}"))
                    if event.get("event") == "step_result":
                        result = event.get("result")
                if result is None:
                    result = self.executor.execute(plan)
                self.root.after(0, self._finish_tool, result)
        except Exception as e:
            self.log.exception("request processing failed")
            traceback.print_exc()
            self.root.after(
                0,
                lambda: self._show_exception(e, "ui", "_process_request"),
            )
            self.root.after(0, self._finish_request)

    def _handle_stream_chunk(self, chunk: str):
        """Handle streaming response chunk."""
        self._assistant_buffer += chunk
        if not self._streaming:
            self._streaming = True
        # Update the last message or create new one
        children = self.chat_frame.winfo_children()
        if children and isinstance(children[-1], MessageBubble):
            children[-1].destroy()
        self._append_assistant_message(self._assistant_buffer, is_streaming=True)

    def _finish_stream(self):
        """Finish streaming response."""
        self.memory.add_assistant_message(self._assistant_buffer)
        self.history_manager.add_message("assistant", self._assistant_buffer)
        if self.settings.get("auto_speak") and self._assistant_buffer.strip():
            threading.Thread(target=self.speech.speak, args=(self._assistant_buffer,), daemon=True).start()
        self._streaming = False
        self._assistant_buffer = ""
        self._finish_request()

    def _finish_tool(self, result):
        """Display tool execution result, and call LLM to generate conversation summary of actions taken."""
        self.status_var.set(STATUS_THINKING)
        self.execution_var.set("Execution: summarization")
        self._update_execution_log("[chat] Generating final response summary")

        summary_input = f"System execute actions outcome: {json.dumps(result, ensure_ascii=False)}. Summarize what was accomplished and state the results clearly for the user."
        
        self._assistant_buffer = ""
        self._streaming = True
        self.cancel_requested = False
        try:
            for chunk in self.ai.stream_response(summary_input, self.memory):
                if self.cancel_requested:
                    break
                self._handle_stream_chunk(chunk)
            self._finish_stream()
        except Exception as e:
            self._show_exception(e, "ai", "stream_response_summary")
            self._finish_stream()

    def _finish_request(self):
        """Clean up after request."""
        self.is_generating = False
        self.input_box.config(state="normal")
        self.send_btn.config(state="normal")
        self.voice_btn.config(state="normal")
        self.execution_var.set("Execution: idle")
        self.file_manager.clear_files()
        self._refresh_attachments_ui()
        self.status_var.set(STATUS_READY)

    def _update_execution_log(self, line: str):
        """Append one line to execution activity panel."""
        if not hasattr(self, "execution_text"):
            return
        self.execution_text.config(state="normal")
        self.execution_text.insert("end", f"\n{line}")
        self.execution_text.see("end")
        self.execution_text.config(state="disabled")
        if hasattr(self, "execution_progress"):
            percent = 0
            if "%" in line:
                chunk = "".join(ch for ch in line if ch.isdigit())
                if chunk:
                    percent = min(100, max(0, int(chunk)))
            elif line.lower().startswith("finished"):
                percent = 100
            if percent:
                self.execution_progress["value"] = percent

    def _show_toast(self, message: str, level: str = "info"):
        """Show a short-lived toast notification."""
        color = STATUS_SUCCESS if level == "success" else (STATUS_ERROR if level == "error" else BG_ACCENT)
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.configure(bg=color)
        toast.attributes("-topmost", True)

        label = tk.Label(toast, text=message, bg=color, fg=TEXT_PRIMARY, font=FONT_SMALL, padx=12, pady=8)
        label.pack()

        x = self.root.winfo_rootx() + self.root.winfo_width() - 280
        y = self.root.winfo_rooty() + 40
        toast.geometry(f"260x40+{x}+{y}")
        toast.after(2200, toast.destroy)

    def _refresh_attachments_ui(self):
        """Redraw attachment chips shown under input area."""
        if not hasattr(self, "attachments_frame"):
            return
        for child in self.attachments_frame.winfo_children():
            child.destroy()

        files = self.file_manager.list_files()
        if not files:
            empty = tk.Label(
                self.attachments_frame,
                text="No files attached",
                bg=BG_SECONDARY,
                fg=TEXT_MUTED,
                font=FONT_SMALL,
                anchor="w",
            )
            empty.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_SMALL)
            return

        row = tk.Frame(self.attachments_frame, bg=BG_SECONDARY)
        row.pack(fill="x", padx=PADDING_SMALL, pady=PADDING_SMALL)
        for idx, info in enumerate(files):
            chip = tk.Frame(row, bg=BG_TERTIARY)
            chip.pack(side="left", padx=(0, PADDING_SMALL))
            label = tk.Label(
                chip,
                text=info.get("name", "file"),
                bg=BG_TERTIARY,
                fg=TEXT_PRIMARY,
                font=FONT_SMALL,
                padx=8,
                pady=4,
            )
            label.pack(side="left")
            remove_btn = tk.Button(
                chip,
                text="x",
                command=lambda i=idx: self._remove_attachment(i),
                bg=BG_TERTIARY,
                fg=TEXT_SECONDARY,
                activebackground=BG_ACCENT,
                activeforeground=TEXT_PRIMARY,
                relief="flat",
                bd=0,
                padx=6,
            )
            remove_btn.pack(side="right")

    def _remove_attachment(self, index: int):
        """Remove one attachment by index."""
        success, msg = self.file_manager.remove_file(index)
        self.status_var.set(msg)
        self._refresh_attachments_ui()

    def _new_chat(self):
        """Start a new chat session."""
        if self.current_session_has_messages():
            self.history_manager.save_session()
        self.history_manager.new_session()
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        self._update_history_list()
        self.status_var.set("New chat started")

    def _show_settings(self):
        """Show settings dialog."""
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("560x620")
        win.configure(bg=BG_PRIMARY)

        tk.Label(win, text="JARVIS Settings", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_HEADING).pack(
            anchor="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

        font_scale_var = tk.DoubleVar(value=self.settings["font_scale"])
        auto_speak_var = tk.BooleanVar(value=self.settings["auto_speak"])
        animations_var = tk.BooleanVar(value=self.settings["animations"])
        timeout_var = tk.IntVar(value=int(self.settings.get("timeout_seconds", 600)))
        model_var = tk.StringVar(value=self.settings.get("llm_model", self.ai.model_name))
        vision_model_var = tk.StringVar(value=self.settings.get("vision_model", "auto"))
        temp_var = tk.DoubleVar(value=float(self.settings.get("temperature", 0.2)))
        ctx_var = tk.IntVar(value=int(self.settings.get("context_length", 8192)))
        ollama_url_var = tk.StringVar(value=self.settings.get("ollama_url", "http://localhost:11434"))
        memory_recent_var = tk.IntVar(value=int(self.settings.get("memory_recent_limit", 40)))
        memory_long_var = tk.IntVar(value=int(self.settings.get("memory_long_term_limit", 2000)))
        voice_var = tk.BooleanVar(value=bool(self.settings.get("voice_enabled", True)))
        mic_var = tk.StringVar(value=self.settings.get("microphone", "default"))
        startup_last_var = tk.BooleanVar(value=bool(self.settings.get("startup_open_last_chat", True)))

        row1 = tk.Frame(win, bg=BG_PRIMARY)
        row1.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row1, text="Font scale", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Scale(row1, from_=0.8, to=1.4, resolution=0.1, orient="horizontal", variable=font_scale_var,
                 bg=BG_PRIMARY, fg=TEXT_PRIMARY, highlightthickness=0, troughcolor=BG_TERTIARY).pack(side="right")

        row_model = tk.Frame(win, bg=BG_PRIMARY)
        row_model.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row_model, text="LLM model", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Entry(row_model, textvariable=model_var, bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat").pack(side="right", fill="x", expand=True)

        row_vmodel = tk.Frame(win, bg=BG_PRIMARY)
        row_vmodel.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row_vmodel, text="Vision model", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Entry(row_vmodel, textvariable=vision_model_var, bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat").pack(side="right", fill="x", expand=True)

        row_temp = tk.Frame(win, bg=BG_PRIMARY)
        row_temp.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row_temp, text="Temperature", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Scale(row_temp, from_=0.0, to=1.0, resolution=0.05, orient="horizontal", variable=temp_var,
             bg=BG_PRIMARY, fg=TEXT_PRIMARY, highlightthickness=0, troughcolor=BG_TERTIARY).pack(side="right")

        row_ctx = tk.Frame(win, bg=BG_PRIMARY)
        row_ctx.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row_ctx, text="Context length", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Spinbox(row_ctx, from_=1024, to=65536, increment=512, textvariable=ctx_var,
               bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat", buttonbackground=BG_ACCENT).pack(side="right")

        row_ollama = tk.Frame(win, bg=BG_PRIMARY)
        row_ollama.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row_ollama, text="Ollama URL", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Entry(row_ollama, textvariable=ollama_url_var, bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat").pack(side="right", fill="x", expand=True)

        row2 = tk.Frame(win, bg=BG_PRIMARY)
        row2.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Checkbutton(row2, text="Enable animations", variable=animations_var,
                       bg=BG_PRIMARY, fg=TEXT_PRIMARY, selectcolor=BG_TERTIARY,
                       activebackground=BG_PRIMARY, activeforeground=TEXT_PRIMARY).pack(anchor="w")

        row3 = tk.Frame(win, bg=BG_PRIMARY)
        row3.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Checkbutton(row3, text="Auto-speak assistant responses", variable=auto_speak_var,
                       bg=BG_PRIMARY, fg=TEXT_PRIMARY, selectcolor=BG_TERTIARY,
                       activebackground=BG_PRIMARY, activeforeground=TEXT_PRIMARY).pack(anchor="w")

        row4 = tk.Frame(win, bg=BG_PRIMARY)
        row4.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row4, text="Timeout (sec)", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Spinbox(row4, from_=60, to=1200, increment=30, textvariable=timeout_var,
                   bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat", buttonbackground=BG_ACCENT).pack(side="right")

        row_mem = tk.Frame(win, bg=BG_PRIMARY)
        row_mem.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row_mem, text="Recent memory limit", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Spinbox(row_mem, from_=10, to=400, increment=10, textvariable=memory_recent_var,
                   bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat", buttonbackground=BG_ACCENT).pack(side="right")

        row_mem_long = tk.Frame(win, bg=BG_PRIMARY)
        row_mem_long.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row_mem_long, text="Long-term memory limit", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Spinbox(row_mem_long, from_=100, to=10000, increment=100, textvariable=memory_long_var,
                   bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat", buttonbackground=BG_ACCENT).pack(side="right")

        row_voice = tk.Frame(win, bg=BG_PRIMARY)
        row_voice.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Checkbutton(row_voice, text="Enable voice", variable=voice_var,
                       bg=BG_PRIMARY, fg=TEXT_PRIMARY, selectcolor=BG_TERTIARY,
                       activebackground=BG_PRIMARY, activeforeground=TEXT_PRIMARY).pack(anchor="w")

        row_mic = tk.Frame(win, bg=BG_PRIMARY)
        row_mic.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row_mic, text="Microphone", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Entry(row_mic, textvariable=mic_var, bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat").pack(side="right", fill="x", expand=True)

        row_start = tk.Frame(win, bg=BG_PRIMARY)
        row_start.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Checkbutton(row_start, text="Open last chat on startup", variable=startup_last_var,
                       bg=BG_PRIMARY, fg=TEXT_PRIMARY, selectcolor=BG_TERTIARY,
                       activebackground=BG_PRIMARY, activeforeground=TEXT_PRIMARY).pack(anchor="w")

        def save_settings():
            self.settings["font_scale"] = float(font_scale_var.get())
            self.settings["animations"] = bool(animations_var.get())
            self.settings["auto_speak"] = bool(auto_speak_var.get())
            self.settings["timeout_seconds"] = int(timeout_var.get())
            self.settings["llm_model"] = model_var.get().strip() or self.ai.model_name
            self.settings["vision_model"] = vision_model_var.get().strip() or "auto"
            self.settings["temperature"] = float(temp_var.get())
            self.settings["context_length"] = int(ctx_var.get())
            self.settings["ollama_url"] = ollama_url_var.get().strip() or "http://localhost:11434"
            self.settings["memory_recent_limit"] = int(memory_recent_var.get())
            self.settings["memory_long_term_limit"] = int(memory_long_var.get())
            self.settings["voice_enabled"] = bool(voice_var.get())
            self.settings["microphone"] = mic_var.get().strip() or "default"
            self.settings["startup_open_last_chat"] = bool(startup_last_var.get())

            self.settings_manager.update(self.settings)
            self.settings_manager.save()

            self.ai.configure(
                model_name=self.settings.get("llm_model"),
                temperature=self.settings.get("temperature"),
                context_length=self.settings.get("context_length"),
            )
            self.vision.set_model(self.settings.get("vision_model", "auto"))
            self.vision.set_timeout(int(self.settings.get("timeout_seconds", 600)))
            self.model_status_var.set(f"Model: {self.ai.model_name}")

            self.status_var.set("Settings saved")
            self._show_toast("Settings saved", "success")
            win.destroy()

        save_btn = RoundedButton(win, text="Save", command=save_settings, width=120, height=34, bg=BG_ACCENT)
        save_btn.pack(pady=PADDING_MEDIUM)

    def _show_memory_panel(self):
        """Show recent memory entries and actions."""
        win = tk.Toplevel(self.root)
        win.title("Memory")
        win.geometry("560x420")
        win.configure(bg=BG_PRIMARY)

        tk.Label(win, text="Recent Memory", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_HEADING).pack(
            anchor="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

        memory_box = tk.Text(
            win,
            wrap="word",
            bg=BG_TERTIARY,
            fg=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=FONT_SMALL,
            padx=PADDING_NORMAL,
            pady=PADDING_NORMAL,
        )
        memory_box.pack(fill="both", expand=True, padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM))

        def refresh_memory_view(query: str = ""):
            memory_box.config(state="normal")
            memory_box.delete("1.0", "end")
            if query.strip():
                hits = self.memory.search_memory(query.strip(), limit=100)
                for bucket, items in hits.items():
                    memory_box.insert("end", f"[{bucket}]\n")
                    for item in items:
                        memory_box.insert("end", f"- {json.dumps(item, ensure_ascii=False)}\n")
                    memory_box.insert("end", "\n")
            else:
                payload = self.memory.get_recent_history(limit=50)
                for item in payload.get("messages", []):
                    role = item.get("role", "system")
                    content = item.get("content", "")
                    memory_box.insert("end", f"[{role}] {content}\n\n")
            memory_box.config(state="disabled")

        refresh_memory_view()

        memory_box.config(state="disabled")

        search_row = tk.Frame(win, bg=BG_PRIMARY)
        search_row.pack(fill="x", padx=PADDING_MEDIUM, pady=(0, PADDING_SMALL))
        query_var = tk.StringVar()
        tk.Entry(search_row, textvariable=query_var, bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat").pack(side="left", fill="x", expand=True)
        RoundedButton(
            search_row,
            text="Search",
            command=lambda: refresh_memory_view(query_var.get()),
            width=100,
            height=32,
            bg=BG_ACCENT,
        ).pack(side="right", padx=(PADDING_SMALL, 0))

        button_row = tk.Frame(win, bg=BG_PRIMARY)
        button_row.pack(fill="x", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM))

        def clear_memory():
            self.memory.clear_history()
            self.status_var.set("Memory cleared")
            win.destroy()

        def export_memory():
            self.status_var.set("Memory persisted to memory.json")
            self._show_toast("Memory exported", "success")

        def summarize_memory():
            summary = self.memory.summarize_memory(max_items=12)
            refresh_memory_view("")
            memory_box.config(state="normal")
            memory_box.insert("1.0", f"[summary]\n{summary}\n\n")
            memory_box.config(state="disabled")

        RoundedButton(button_row, text="Clear Memory", command=clear_memory, width=140, height=34, bg=STATUS_ERROR).pack(side="left")
        RoundedButton(button_row, text="Export", command=export_memory, width=120, height=34, bg=BG_ACCENT).pack(side="left", padx=PADDING_SMALL)
        RoundedButton(button_row, text="Summarize", command=summarize_memory, width=120, height=34, bg=BG_TERTIARY).pack(side="left", padx=PADDING_SMALL)

    def _show_dev_dashboard(self):
        """Displays real-time hardware status metrics, benchmarks history, and diagnostics reports."""
        win = tk.Toplevel(self.root)
        win.title("Developer Dashboard")
        win.geometry("640x520")
        win.configure(bg=BG_PRIMARY)

        tk.Label(win, text="🛠️ System Health & Performance benchmarks", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_HEADING).pack(
            anchor="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

        display_box = tk.Text(
            win,
            wrap="word",
            bg=BG_TERTIARY,
            fg=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=FONT_SMALL,
            padx=PADDING_NORMAL,
            pady=PADDING_NORMAL,
        )
        display_box.pack(fill="both", expand=True, padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM))

        def refresh_dashboard():
            display_box.config(state="normal")
            display_box.delete("1.0", "end")
            
            # Fetch diagnostic status
            diags = self.diagnostics.run_diagnostics()
            health = self.health_manager.check_health()
            avg_benchmarks = self.benchmarks.get_averages()

            display_box.insert("end", "[SYSTEM HEALTH MONITOR]\n")
            display_box.insert("end", f"- Host Status: {health.get('status')}\n")
            display_box.insert("end", f"- CPU usage: {health.get('cpu_percent')}%\n")
            display_box.insert("end", f"- RAM usage: {health.get('memory_percent')}%\n")
            display_box.insert("end", f"- VRAM usage: {health.get('vram_percent')}%\n")
            display_box.insert("end", f"- Ollama state: {health.get('ollama_status')}\n")
            display_box.insert("end", f"- Available Local models: {health.get('available_models')}\n\n")

            display_box.insert("end", "[PERFORMANCE BENCHMARKS - LATENCY AVERAGES]\n")
            for metric, avg in avg_benchmarks.items():
                display_box.insert("end", f"- {metric}: {avg:.3f} seconds\n")
            display_box.insert("end", "\n")

            display_box.insert("end", "[DIAGNOSTICS CHECKS]\n")
            display_box.insert("end", f"- Process RSS RAM: {diags.get('rss_mb')} MB\n")
            if diags.get("success"):
                display_box.insert("end", "- All diagnostic parameters clean.\n")
            else:
                display_box.insert("end", "- Detected anomalies:\n")
                for issue in diags.get("issues", []):
                    display_box.insert("end", f"  * {issue}\n")

            display_box.config(state="disabled")

        refresh_dashboard()

        # Add manual reload button
        btn_row = tk.Frame(win, bg=BG_PRIMARY)
        btn_row.pack(fill="x", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM))
        RoundedButton(btn_row, text="Refresh Status", command=refresh_dashboard, width=140, height=34, bg=BG_ACCENT).pack(side="left")

    def _clear_chat(self, event=None):
        """Clear current chat canvas quickly."""
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        self.status_var.set("Chat cleared")
        return "break"

    def _on_cancel_current(self, event=None):
        """Cancel current in-flight request from UI perspective."""
        if self.is_generating:
            self.cancel_requested = True
            if self.current_task_id:
                self.task_queue.cancel(self.current_task_id)
            self.is_generating = False
            self.status_var.set("Cancelled")
            self.execution_var.set("Execution: cancelled")
            self.input_box.config(state="normal")
            self.send_btn.config(state="normal")
            self.voice_btn.config(state="normal")
            return "break"
        return

    def _retry_last_task(self):
        """Retry the most recent queued task."""
        task_id = self.task_queue.retry_latest()
        if task_id:
            self.current_task_id = task_id
            self._show_toast("Retry submitted", "info")

    def _update_history_list(self):
        """Update the history list in sidebar."""
        for widget in self.history_list_frame.winfo_children():
            widget.destroy()

        toolbar = tk.Frame(self.history_list_frame, bg=BG_SECONDARY)
        toolbar.pack(fill="x", padx=PADDING_SMALL, pady=PADDING_SMALL)
        tk.Button(
            toolbar,
            text="Import",
            command=self._import_conversation,
            bg=BG_TERTIARY,
            fg=TEXT_PRIMARY,
            relief="flat",
            bd=0,
        ).pack(side="left")

        sessions = self.history_manager.get_sessions()
        query = self.history_search_var.get().strip().lower() if hasattr(self, "history_search_var") else ""
        if query:
            sessions = [s for s in sessions if query in s.get("title", "").lower()]
        
        # Display up to 15 sessions in reverse order
        for session in reversed(sessions[-15:]):
            title = session["title"]
            is_pinned = session.get("pinned", False)
            display_title = f"📌 {title}" if is_pinned else f"💬 {title}"
            
            item_row = tk.Frame(self.history_list_frame, bg=BG_SECONDARY)
            item_row.pack(fill="x", padx=PADDING_SMALL, pady=PADDING_SMALL)

            # Modern clean button with background corresponding to active state
            is_selected = (self.selected_session_id == session["id"])
            btn_bg = BG_TERTIARY if is_selected else BG_SECONDARY
            btn_fg = TEXT_PRIMARY if is_selected else TEXT_SECONDARY

            session_btn = tk.Button(
                item_row,
                text=display_title,
                bg=btn_bg,
                fg=btn_fg,
                font=FONT_SMALL,
                relief="flat",
                bd=0,
                padx=PADDING_NORMAL,
                pady=PADDING_SMALL,
                anchor="w",
                command=lambda sid=session["id"]: self._load_session(sid),
                cursor="hand2"
            )
            session_btn.pack(fill="x", expand=True)

            # Create context menu
            menu = tk.Menu(self.root, tearoff=0, bg=BG_SECONDARY, fg=TEXT_PRIMARY, activebackground=BG_ACCENT)
            menu.add_command(label="📌 Pin / Unpin", command=lambda sid=session["id"]: (self._pin_conversation(sid), self._update_history_list()))
            menu.add_command(label="✏️ Rename", command=lambda sid=session["id"]: (self._rename_conversation(sid), self._update_history_list()))
            menu.add_command(label="📤 Export JSON", command=lambda sid=session["id"]: self._export_conversation(sid))
            menu.add_separator()
            menu.add_command(label="❌ Delete Chat", command=lambda sid=session["id"]: (self._delete_conversation(sid), self._update_history_list()))

            # Binding right-click context menu
            session_btn.bind("<Button-3>", lambda e, m=menu: m.post(e.x_root, e.y_root))

    def _load_session(self, session_id: int):
        """Load a previous session."""
        self.selected_session_id = session_id
        messages = self.history_manager.get_session(session_id)
        
        # Clear existing conversation display
        for widget in self.chat_frame.winfo_children():
            widget.destroy()

        if messages:
            for msg in messages:
                if msg["role"] == "user":
                    self._append_user_message(msg["content"])
                else:
                    self._append_assistant_message(msg["content"])
        self._update_history_list()

    def _rename_conversation(self, session_id: int):
        """Rename selected conversation."""
        new_name = simpledialog.askstring("Rename", "New conversation title:")
        if new_name:
            self.history_manager.rename_session(session_id, new_name)
            self._update_history_list()

    def _delete_conversation(self, session_id: int):
        """Delete selected conversation."""
        self.history_manager.delete_session(session_id)
        self._update_history_list()

    def _pin_conversation(self, session_id: int):
        """Pin/unpin selected conversation."""
        self.history_manager.pin_session(session_id)
        self._update_history_list()

    def _export_conversation(self, session_id: int):
        """Export selected conversation to JSON file."""
        content = self.history_manager.export_session(session_id, format="json")
        if not content:
            return
        file_path = filedialog.asksaveasfilename(
            title="Export conversation",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if file_path:
            Path(file_path).write_text(content, encoding="utf-8")
            self._show_toast("Conversation exported", "success")

    def _import_conversation(self):
        """Import conversation from JSON file."""
        file_path = filedialog.askopenfilename(title="Import conversation", filetypes=[("JSON", "*.json")])
        if file_path and self.history_manager.import_session(file_path):
            self._update_history_list()
            self._show_toast("Conversation imported", "success")

    def current_session_has_messages(self) -> bool:
        """Check if current session has messages."""
        return len(self.chat_frame.winfo_children()) > 0

    # =========================================================================
    # MESSAGE DISPLAY
    # =========================================================================

    def _append_user_message(self, text: str):
        """Add user message to chat."""
        bubble = MessageBubble(
            self.chat_frame,
            text=text,
            is_user=True,
            timestamp=datetime.now().strftime("%H:%M"),
        )
        bubble.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        self.chat_frame.update_idletasks()

    def _append_assistant_message(self, text: str, is_streaming: bool = False):
        """Add assistant message to chat."""
        bubble = MessageBubble(
            self.chat_frame,
            text=text,
            is_user=False,
            timestamp=datetime.now().strftime("%H:%M") if not is_streaming else "",
        )
        bubble.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        self.chat_frame.update_idletasks()

    def _on_paste_clipboard(self, event=None):
        """Handle Ctrl+V to paste images from clipboard."""
        try:
            # Try to get image from clipboard
            # This works on Windows via PIL
            from PIL import ImageGrab
            
            img = ImageGrab.grabclipboard()
            if img and img.mode in ('RGB', 'RGBA'):
                # Save to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    img.save(f, 'PNG')
                    temp_path = f.name
                
                # Add to file manager
                success, msg = self.file_manager.add_file(temp_path)
                self.status_var.set(msg)
                self._refresh_attachments_ui()
                self.root.after(0, lambda: None)  # Allow normal paste to continue if not image
                return "break"  # Prevent normal paste
            else:
                # Not an image, allow normal text paste
                return
        except Exception as e:
            # Allow normal paste if image grab fails
            pass
    
    def _on_drop_files(self, event=None):
        """Handle drag & drop files onto input area."""
        try:
            if not event or not event.data:
                return
            
            # Parse dropped file paths
            files = self.root.tk.splitlist(event.data)
            for file_path in files:
                # Clean up path (remove curly braces if present)
                file_path = file_path.strip('{}')
                if os.path.exists(file_path):
                    success, msg = self.file_manager.add_file(file_path)
                    self.status_var.set(msg)
            self._refresh_attachments_ui()
        except Exception as e:
            self.status_var.set(f"Drop error: {e}")

    def _check_ollama_health(self):
        """Perform background verification of Ollama server and configured model status."""
        try:
            self.status_var.set("Checking local AI services...")
            if not self.ai.is_online():
                self.status_var.set("⚠️ Ollama is offline")
                self._update_execution_log("[health] Warning: Local Ollama server is offline.")
                self.root.after(0, lambda: self._show_toast("Ollama is offline. Please make sure Ollama is running.", "error"))
                return
            
            if not self.ai.check_model_available():
                self.status_var.set(f"⚠️ Model '{self.ai.model_name}' missing")
                self._update_execution_log(f"[health] Warning: Configured model '{self.ai.model_name}' not found.")
                self.root.after(0, lambda: self._show_toast(f"Model '{self.ai.model_name}' not found. Please pull it.", "error"))
                return
            
            self.status_var.set(STATUS_READY)
            self._update_execution_log("[health] Ollama and model status OK")
        except Exception as e:
            self.status_var.set("Health check error")
            self._update_execution_log(f"[health] Error: {e}")

    def _show_exception(self, e: Exception, module: str, function: str):
        """Log error traceback, diagnose with AutoDebugger, and append formatted message."""
        diag = self.debugger.debug_exception(e, f"{module}.{function}")
        tb = diag.get("traceback", traceback.format_exc())
        
        recovery_status = ""
        if diag.get("recovery_attempted"):
            status_text = "Success" if diag.get("recovery_success") else "Failed"
            recovery_status = f"- **Auto-Recovery Attempt**: {status_text} (Action: `{diag.get('suggested_action')}`)\n"

        error_msg = (
            f"⚠️ **Error in JARVIS**\n\n"
            f"- **Module**: `{module}`\n"
            f"- **Function**: `{function}`\n"
            f"- **Details**: {diag.get('exception_message', str(e))}\n"
            f"- **Probable Cause**: {diag.get('probable_cause')}\n"
            f"- **Suggested Action**: {diag.get('suggested_action')}\n"
            f"{recovery_status}\n"
            f"**Traceback**:\n```\n{tb}```"
        )
        self.root.after(0, lambda: self._append_assistant_message(error_msg))

    def _on_close_attempt(self):
        """Stop background threads clean and exit."""
        try:
            self.continuous_observer.stop()
            self.voice_listener.stop()
        except Exception:
            pass
        self.root.destroy()

    # =========================================================================
    # APP LIFECYCLE
    # =========================================================================

    def run(self):
        """Launch the application."""
        self.root.mainloop()
