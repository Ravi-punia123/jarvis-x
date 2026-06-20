"""Rounded button and canvas-based UI components for modern appearance."""

import tkinter as tk
from tkinter import ttk
from ui_theme import *


class RoundedButton(tk.Canvas):
    """A button with rounded corners using Canvas drawing."""

    def __init__(
        self,
        parent,
        text="",
        command=None,
        bg=BUTTON_BG,
        fg=BUTTON_TEXT,
        hover_bg=BUTTON_HOVER,
        active_bg=BUTTON_ACTIVE,
        width=120,
        height=36,
        radius=RADIUS_NORMAL,
        font=FONT_BODY_BOLD,
        **kwargs,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=BG_SECONDARY,
            highlightthickness=0,
            relief="flat",
            bd=0,
        )
        self.text = text
        self.command = command
        self.bg = bg
        self.fg = fg
        self.hover_bg = hover_bg
        self.active_bg = active_bg
        self.radius = radius
        self.font = font
        self.is_hovered = False
        self.is_active = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            w, h = 120, 36

        if self.is_active:
            current_bg = self.active_bg
        elif self.is_hovered:
            current_bg = self.hover_bg
        else:
            current_bg = self.bg

        self.create_arc(
            (0, 0, self.radius * 2, self.radius * 2),
            start=90,
            extent=90,
            fill=current_bg,
            outline=current_bg,
        )
        self.create_arc(
            (w - self.radius * 2, 0, w, self.radius * 2),
            start=0,
            extent=90,
            fill=current_bg,
            outline=current_bg,
        )
        self.create_arc(
            (w - self.radius * 2, h - self.radius * 2, w, h),
            start=270,
            extent=90,
            fill=current_bg,
            outline=current_bg,
        )
        self.create_arc(
            (0, h - self.radius * 2, self.radius * 2, h),
            start=180,
            extent=90,
            fill=current_bg,
            outline=current_bg,
        )

        self.create_rectangle(
            (self.radius, 0, w - self.radius, h),
            fill=current_bg,
            outline=current_bg,
        )
        self.create_rectangle(
            (0, self.radius, w, h - self.radius),
            fill=current_bg,
            outline=current_bg,
        )

        if self.text:
            self.create_text(
                (w / 2, h / 2),
                text=self.text,
                fill=self.fg,
                font=self.font,
                anchor="center",
            )

    def _on_enter(self, event):
        self.is_hovered = True
        self._draw()

    def _on_leave(self, event):
        self.is_hovered = False
        self._draw()

    def _on_press(self, event):
        self.is_active = True
        self._draw()

    def _on_release(self, event):
        self.is_active = False
        self._draw()
        if self.command:
            self.command()

    def configure(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "command" in kwargs:
            self.command = kwargs["command"]
        self._draw()


class LoadingIndicator(tk.Canvas):
    """Animated spinning indicator for loading states."""

    def __init__(self, parent, size=24, color=STATUS_THINKING, **kwargs):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=BG_PRIMARY,
            highlightthickness=0,
            relief="flat",
            bd=0,
        )
        self.size = size
        self.color = color
        self.angle = 0
        self.is_active = False

    def start(self):
        """Begin the loading animation."""
        if not self.is_active:
            self.is_active = True
            self._animate()

    def stop(self):
        """Stop the loading animation."""
        self.is_active = False
        self.delete("all")

    def _animate(self):
        if not self.is_active:
            return
        self.delete("all")
        cx, cy = self.size / 2, self.size / 2
        r = self.size / 3
        import math

        for i in range(12):
            angle = math.radians((self.angle + i * 30) % 360)
            x1 = cx + r * math.cos(angle)
            y1 = cy + r * math.sin(angle)
            x2 = cx + (r + 4) * math.cos(angle)
            y2 = cy + (r + 4) * math.sin(angle)
            opacity = int(255 * (1 - i / 12))
            self.create_line((x1, y1, x2, y2), fill=self.color, width=2)

        self.angle = (self.angle + 30) % 360
        self.after(ANIMATION_DURATION_FAST, self._animate)


class MessageBubble(tk.Frame):
    """A message bubble for chat display (user or assistant)."""

    def __init__(
        self,
        parent,
        text="",
        is_user=False,
        timestamp="",
        **kwargs,
    ):
        super().__init__(parent, bg=BG_PRIMARY, **kwargs)
        self.is_user = is_user

        # Container for alignment
        container = tk.Frame(self, bg=BG_PRIMARY)
        container.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_SMALL)

        if is_user:
            container.pack(anchor="e")
        else:
            container.pack(anchor="w")

        # Bubble background
        bubble_bg = BUBBLE_USER_BG if is_user else BUBBLE_ASSISTANT_BG
        bubble_frame = tk.Frame(container, bg=bubble_bg, relief="flat", bd=0, padx=2, pady=2)
        bubble_frame.pack(side="left" if not is_user else "right", fill="both", expand=True)

        header_bar = tk.Frame(bubble_frame, bg=bubble_bg)
        header_bar.pack(fill="x", side="top", padx=PADDING_SMALL, pady=(PADDING_SMALL, 0))

        if not is_user:
            copy_btn = tk.Button(
                header_bar,
                text="📋 Copy",
                command=lambda t=text: self._copy_text(t),
                bg=bubble_bg,
                fg=TEXT_SECONDARY,
                activebackground=BG_TERTIARY,
                activeforeground=TEXT_PRIMARY,
                relief="flat",
                bd=0,
                padx=6,
                pady=2,
                font=FONT_TINY,
                cursor="hand2"
            )
            copy_btn.pack(side="right")

        # Text in bubble: switch to monospace block rendering for code/table content.
        has_code_block = "```" in text
        looks_like_table = "|" in text and "\n" in text
        if has_code_block or looks_like_table:
            content = text.replace("```", "")
            if has_code_block:
                copy_code_btn = tk.Button(
                    header_bar,
                    text="📋 Copy Code",
                    command=lambda t=content: self._copy_text(t),
                    bg=bubble_bg,
                    fg=TEXT_SECONDARY,
                    activebackground=BG_TERTIARY,
                    activeforeground=TEXT_PRIMARY,
                    relief="flat",
                    bd=0,
                    padx=6,
                    pady=2,
                    font=FONT_TINY,
                    cursor="hand2"
                )
                copy_code_btn.pack(side="right", padx=(0, PADDING_SMALL))

            text_block = tk.Text(
                bubble_frame,
                bg=BG_PRIMARY if not is_user else bubble_bg,
                fg=TEXT_PRIMARY,
                font=FONT_MONOSPACE,
                wrap="word",
                relief="flat",
                bd=0,
                height=min(12, max(2, content.count("\n") + 1)),
                padx=PADDING_MEDIUM,
                pady=PADDING_NORMAL,
                insertbackground=TEXT_PRIMARY
            )
            text_block.insert("1.0", content)
            text_block.config(state="disabled")
            text_block.pack(fill="both", expand=True, padx=PADDING_SMALL, pady=PADDING_SMALL)
        else:
            rendered_text = self._render_markdown_like(text)
            text_label = tk.Label(
                bubble_frame,
                text=rendered_text,
                bg=bubble_bg,
                fg=TEXT_PRIMARY,
                font=FONT_BODY,
                wraplength=600,
                justify="left",
                padx=PADDING_MEDIUM,
                pady=PADDING_NORMAL,
            )
            text_label.pack(fill="both", expand=True)

        # Timestamp
        if timestamp:
            ts_label = tk.Label(
                container,
                text=timestamp,
                bg=BG_PRIMARY,
                fg=TEXT_MUTED,
                font=FONT_TINY,
            )
            ts_label.pack(anchor="se" if is_user else "sw", padx=PADDING_SMALL)

    def _copy_text(self, text: str):
        """Copy bubble text to clipboard."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
        except Exception:
            return

    def _render_markdown_like(self, text: str) -> str:
        """Small markdown-to-plain-text renderer for headings/lists/bold markers."""
        lines = []
        for line in str(text).splitlines():
            cleaned = line
            if cleaned.startswith("#"):
                cleaned = cleaned.lstrip("#").strip().upper()
            cleaned = cleaned.replace("**", "")
            cleaned = cleaned.replace("__", "")
            lines.append(cleaned)
        return "\n".join(lines)


class StatusIndicator(tk.Frame):
    """Status indicator with animated icon and text."""

    def __init__(self, parent, text="", status_type="thinking", **kwargs):
        super().__init__(parent, bg=BG_SECONDARY, **kwargs)
        self.status_type = status_type
        self.text = text

        # Choose color based on status
        color_map = {
            "thinking": STATUS_THINKING,
            "executing": STATUS_LOADING,
            "success": STATUS_SUCCESS,
            "error": STATUS_ERROR,
            "warning": STATUS_WARNING,
        }
        color = color_map.get(status_type, STATUS_THINKING)

        # Loading indicator or static icon
        if status_type in ("thinking", "executing"):
            loader = LoadingIndicator(self, size=16, color=color)
            loader.pack(side="left", padx=PADDING_SMALL)
            loader.start()
        else:
            icon_map = {
                "success": "✓",
                "error": "✗",
                "warning": "⚠",
            }
            icon = icon_map.get(status_type, "•")
            icon_label = tk.Label(
                self,
                text=icon,
                bg=BG_SECONDARY,
                fg=color,
                font=FONT_BODY_BOLD,
                padx=PADDING_SMALL,
            )
            icon_label.pack(side="left")

        # Status text
        status_label = tk.Label(
            self,
            text=text,
            bg=BG_SECONDARY,
            fg=TEXT_PRIMARY,
            font=FONT_SMALL,
        )
        status_label.pack(side="left", padx=PADDING_SMALL)
