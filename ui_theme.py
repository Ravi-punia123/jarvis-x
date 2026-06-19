"""Modern dark theme constants and styling for the JARVIS UI."""

# ============================================================================
# COLORS
# ============================================================================

# Background
BG_PRIMARY = "#1e1e1e"        # Main background (very dark)
BG_SECONDARY = "#2d2d2d"      # Secondary background (input area, panels)
BG_TERTIARY = "#3e3e3e"       # Tertiary (hover, active)
BG_ACCENT = "#0d7377"         # Accent/highlight (buttons, active)

# Text
TEXT_PRIMARY = "#ffffff"      # Main text (white)
TEXT_SECONDARY = "#b0b0b0"    # Dimmed text (timestamps, secondary info)
TEXT_MUTED = "#808080"        # Very dim text (placeholders, hints)

# Chat bubbles
BUBBLE_USER_BG = "#0d7377"    # User message background (teal)
BUBBLE_ASSISTANT_BG = "#2d2d2d"  # Assistant message background (dark)
BUBBLE_SYSTEM_BG = "#3e2800"  # System message background (orange-brown)

# Status & indicators
STATUS_SUCCESS = "#4ade80"    # Green (success, checkmark)
STATUS_ERROR = "#f87171"      # Red (error, failed)
STATUS_WARNING = "#facc15"    # Yellow (warning)
STATUS_THINKING = "#60a5fa"   # Blue (thinking, processing)
STATUS_LOADING = "#a78bfa"    # Purple (loading, inference)

# UI Elements
BUTTON_BG = "#0d7377"         # Button background
BUTTON_HOVER = "#0f9099"      # Button hover (lighter)
BUTTON_ACTIVE = "#075c63"     # Button active (darker)
BUTTON_TEXT = TEXT_PRIMARY

SCROLLBAR_BG = BG_SECONDARY
SCROLLBAR_THUMB = "#555555"

BORDER_COLOR = "#444444"
SEPARATOR_COLOR = "#444444"

# ============================================================================
# FONTS
# ============================================================================

FONT_FAMILY = "Segoe UI"

# Font sizes (in points)
FONT_SIZE_TITLE = 18
FONT_SIZE_HEADING = 14
FONT_SIZE_BODY = 11
FONT_SIZE_SMALL = 10
FONT_SIZE_TINY = 9

# Font styles
FONT_TITLE = (FONT_FAMILY, FONT_SIZE_TITLE, "bold")
FONT_HEADING = (FONT_FAMILY, FONT_SIZE_HEADING, "bold")
FONT_BODY = (FONT_FAMILY, FONT_SIZE_BODY)
FONT_BODY_BOLD = (FONT_FAMILY, FONT_SIZE_BODY, "bold")
FONT_SMALL = (FONT_FAMILY, FONT_SIZE_SMALL)
FONT_SMALL_BOLD = (FONT_FAMILY, FONT_SIZE_SMALL, "bold")
FONT_TINY = (FONT_FAMILY, FONT_SIZE_TINY)
FONT_MONOSPACE = ("Consolas", FONT_SIZE_SMALL)

# ============================================================================
# DIMENSIONS
# ============================================================================

# Spacing
PADDING_SMALL = 4
PADDING_NORMAL = 8
PADDING_MEDIUM = 12
PADDING_LARGE = 16

# Sizes
SIDEBAR_WIDTH = 280
INPUT_HEIGHT = 100
STATUS_BAR_HEIGHT = 28
BUTTON_HEIGHT = 36
BUTTON_WIDTH = 100

# Border radius (used by canvas/button roundness)
RADIUS_SMALL = 4
RADIUS_NORMAL = 8
RADIUS_LARGE = 12

# ============================================================================
# ANIMATIONS
# ============================================================================

ANIMATION_DURATION_FAST = 200      # milliseconds
ANIMATION_DURATION_NORMAL = 300
ANIMATION_DURATION_SLOW = 500

# ============================================================================
# WINDOW
# ============================================================================

WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 600
WINDOW_DEFAULT_WIDTH = 1200
WINDOW_DEFAULT_HEIGHT = 800
