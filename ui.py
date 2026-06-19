"""Modern AI desktop assistant UI - Main application window."""

import threading
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime
from typing import Optional
import traceback
import os
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
        self.vision = VisionManager()
        self.speech = SpeechManager()
        self.file_manager = FileManager()
        self.history_manager = HistoryManager()

        # UI state
        self.status_var = tk.StringVar(value=STATUS_READY)
        self.model_status_var = tk.StringVar(value=f"Model: {self.ai.model_name}")
        self.inference_var = tk.StringVar(value="Inference: idle")
        self.execution_var = tk.StringVar(value="Execution: idle")
        self.is_generating = False
        self._streaming = False
        self._assistant_buffer = ""
        self.cancel_requested = False
        self.settings = {
            "font_scale": 1.0,
            "animations": True,
            "vision_timeout": 600,
            "auto_speak": False,
        }

        # Build UI
        self._build_ui()
        self._bind_shortcuts()
        self.history_manager.new_session()

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

        return sidebar

    def _build_header(self, parent):
        """Build the header with model and status info."""
        header = tk.Frame(parent, bg=BG_SECONDARY)

        # Model indicator
        model_label = tk.Label(
            header,
            textvariable=self.model_status_var,
            bg=BG_SECONDARY,
            fg=TEXT_SECONDARY,
            font=FONT_SMALL,
        )
        model_label.pack(side="left", padx=PADDING_NORMAL, pady=PADDING_SMALL)

        # Separator
        sep = tk.Frame(header, bg=SEPARATOR_COLOR, width=1)
        sep.pack(side="left", fill="y", padx=PADDING_NORMAL)

        # Vision status
        self.vision_status = tk.Label(
            header,
            text="👁️ Vision Ready",
            bg=BG_SECONDARY,
            fg=STATUS_SUCCESS,
            font=FONT_SMALL,
        )
        self.vision_status.pack(side="left", padx=PADDING_NORMAL, pady=PADDING_SMALL)

        infer_label = tk.Label(
            header,
            textvariable=self.inference_var,
            bg=BG_SECONDARY,
            fg=TEXT_MUTED,
            font=FONT_SMALL,
        )
        infer_label.pack(side="right", padx=PADDING_NORMAL, pady=PADDING_SMALL)

        return header

    def _build_input_area(self, parent):
        """Build the multimodal input area."""
        input_frame = tk.Frame(parent, bg=BG_SECONDARY)

        # Text input with frame for styling
        input_inner = tk.Frame(input_frame, bg=BG_SECONDARY)
        input_inner.pack(fill="both", expand=True, padx=0, pady=0)

        self.input_box = tk.Text(
            input_inner,
            height=4,
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
        self.input_box.bind("<Control-Return>", self._on_send)
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
        title = tk.Label(
            panel,
            text="Execution",
            bg=BG_SECONDARY,
            fg=TEXT_SECONDARY,
            font=FONT_SMALL,
            anchor="w",
        )
        title.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_SMALL, 0))

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
        self.execution_text.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_SMALL)
        self.execution_text.insert("1.0", "Waiting for next request...")
        self.execution_text.config(state="disabled")

        return panel

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
        self._append_user_message(display_text)
        self.input_box.delete("1.0", "end")
        self.input_box.config(state="disabled")
        self.send_btn.config(state="disabled")
        self.voice_btn.config(state="disabled")
        self.is_generating = True
        self.status_var.set(STATUS_TYPING)

        threading.Thread(
            target=self._process_request,
            args=(full_message,),
            daemon=True,
        ).start()

    def _on_upload(self):
        """Open file dialog for upload."""
        files = filedialog.askopenfilenames(
            title="Add files",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.gif *.webp"),
                ("Documents", "*.pdf *.txt *.docx *.doc *.xlsx *.csv"),
                ("Code", "*.py *.js *.ts *.java *.cpp"),
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

    def _process_request(self, prompt: str):
        """Process user request in background thread."""
        try:
            self.execution_var.set("Execution: planning")
            self._update_execution_log("[planner] Building action plan")
            plan = self.planner.plan(prompt)

            if isinstance(plan, dict) and plan.get("action") == "chat":
                self.status_var.set(STATUS_THINKING)
                self.execution_var.set("Execution: chat")
                self._update_execution_log("[chat] Streaming model response")
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
                        lambda: self._append_assistant_message(f"Error: {e}"),
                    )
                    self.root.after(0, self._finish_stream)
            else:
                self.status_var.set("Executing...")
                self.execution_var.set("Execution: tools")
                self._update_execution_log("[executor] Running tool pipeline")
                result = self.executor.execute(plan)
                self.root.after(0, self._finish_tool, result)
        except Exception as e:
            traceback.print_exc()
            self.root.after(
                0,
                lambda: self._append_assistant_message(f"Error: {e}"),
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
        if self.settings.get("auto_speak") and self._assistant_buffer.strip():
            threading.Thread(target=self.speech.speak, args=(self._assistant_buffer,), daemon=True).start()
        self._streaming = False
        self._assistant_buffer = ""
        self._finish_request()

    def _finish_tool(self, result):
        """Display tool execution result."""
        if isinstance(result, dict) and isinstance(result.get("steps"), list):
            total = max(len(result["steps"]), 1)
            for idx, step in enumerate(result["steps"], start=1):
                symbol = "✓" if step.get("success") else "✗"
                pct = int((idx / total) * 100)
                msg = f"{symbol} [{pct}%] {step.get('message', 'Done')}"
                self._append_assistant_message(msg)
                self._update_execution_log(msg)
        else:
            message = (
                result.get("message")
                if isinstance(result, dict) and result.get("success")
                else (result.get("error") if isinstance(result, dict) else str(result))
            )
            self._append_assistant_message(message or "Done.")
            self._update_execution_log(message or "Done.")
            if self.settings.get("auto_speak") and (message or "").strip():
                threading.Thread(target=self.speech.speak, args=(message,), daemon=True).start()
        self._finish_request()

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
        win.geometry("420x320")
        win.configure(bg=BG_PRIMARY)

        tk.Label(win, text="JARVIS Settings", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_HEADING).pack(
            anchor="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

        font_scale_var = tk.DoubleVar(value=self.settings["font_scale"])
        auto_speak_var = tk.BooleanVar(value=self.settings["auto_speak"])
        animations_var = tk.BooleanVar(value=self.settings["animations"])
        timeout_var = tk.IntVar(value=self.settings["vision_timeout"])

        row1 = tk.Frame(win, bg=BG_PRIMARY)
        row1.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)
        tk.Label(row1, text="Font scale", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Scale(row1, from_=0.8, to=1.4, resolution=0.1, orient="horizontal", variable=font_scale_var,
                 bg=BG_PRIMARY, fg=TEXT_PRIMARY, highlightthickness=0, troughcolor=BG_TERTIARY).pack(side="right")

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
        tk.Label(row4, text="Vision timeout (sec)", bg=BG_PRIMARY, fg=TEXT_PRIMARY, font=FONT_SMALL).pack(side="left")
        tk.Spinbox(row4, from_=60, to=1200, increment=30, textvariable=timeout_var,
                   bg=BG_TERTIARY, fg=TEXT_PRIMARY, relief="flat", buttonbackground=BG_ACCENT).pack(side="right")

        def save_settings():
            self.settings["font_scale"] = float(font_scale_var.get())
            self.settings["animations"] = bool(animations_var.get())
            self.settings["auto_speak"] = bool(auto_speak_var.get())
            self.settings["vision_timeout"] = int(timeout_var.get())
            self.status_var.set("Settings saved")
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

        for item in self.memory.get_recent_history(limit=50):
            role = item.get("role", "system")
            content = item.get("content", "")
            memory_box.insert("end", f"[{role}] {content}\n\n")

        memory_box.config(state="disabled")

        button_row = tk.Frame(win, bg=BG_PRIMARY)
        button_row.pack(fill="x", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM))

        def clear_memory():
            self.memory.clear_history()
            self.status_var.set("Memory cleared")
            win.destroy()

        def export_memory():
            self.status_var.set("Memory persisted to memory.json")

        RoundedButton(button_row, text="Clear Memory", command=clear_memory, width=140, height=34, bg=STATUS_ERROR).pack(side="left")
        RoundedButton(button_row, text="Export", command=export_memory, width=120, height=34, bg=BG_ACCENT).pack(side="left", padx=PADDING_SMALL)

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
            self.is_generating = False
            self.status_var.set("Cancelled")
            self.execution_var.set("Execution: cancelled")
            self.input_box.config(state="normal")
            self.send_btn.config(state="normal")
            self.voice_btn.config(state="normal")
            return "break"
        return

    def _update_history_list(self):
        """Update the history list in sidebar."""
        for widget in self.history_list_frame.winfo_children():
            widget.destroy()

        sessions = self.history_manager.get_sessions()
        query = self.history_search_var.get().strip().lower() if hasattr(self, "history_search_var") else ""
        if query:
            sessions = [s for s in sessions if query in s.get("title", "").lower()]
        for session in reversed(sessions[-5:]):
            title = session["title"]
            if session.get("pinned"):
                title = f"* {title}"
            session_btn = tk.Button(
                self.history_list_frame,
                text=title,
                bg=BG_TERTIARY,
                fg=TEXT_PRIMARY,
                font=FONT_SMALL,
                relief="flat",
                bd=0,
                padx=PADDING_NORMAL,
                pady=PADDING_SMALL,
                anchor="w",
                command=lambda sid=session["id"]: self._load_session(sid),
            )
            session_btn.pack(fill="x", padx=PADDING_SMALL, pady=PADDING_SMALL)

    def _load_session(self, session_id: int):
        """Load a previous session."""
        messages = self.history_manager.get_session(session_id)
        if messages:
            for widget in self.chat_frame.winfo_children():
                widget.destroy()
            for msg in messages:
                if msg["role"] == "user":
                    self._append_user_message(msg["content"])
                else:
                    self._append_assistant_message(msg["content"])

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

    # =========================================================================
    # APP LIFECYCLE
    # =========================================================================

    def run(self):
        """Launch the application."""
        self.root.mainloop()
