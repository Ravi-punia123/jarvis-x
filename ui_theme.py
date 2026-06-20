"""Modern dark theme constants and styling for the JARVIS UI."""

# ============================================================================
# COLORS
# ============================================================================

# Premium Slate-based Dark Palette
BG_PRIMARY = "#090d16"          # Deep cosmic background
BG_SECONDARY = "#111827"        # Cards and sidebars (Slate 900)
BG_TERTIARY = "#1f2937"         # Inputs, active selections, and borders (Slate 800)
BG_ACCENT = "#3b82f6"           # Accent blue (Indigo/Blue 500)

# Text
TEXT_PRIMARY = "#f9fafb"        # High-contrast off-white (Gray 50)
TEXT_SECONDARY = "#9ca3af"      # Dimmed readable text (Gray 400)
TEXT_MUTED = "#6b7280"          # Placeholders, timestamps, borders (Gray 500)

# Chat bubbles
BUBBLE_USER_BG = "#2563eb"      # Soft royal blue for user messages
BUBBLE_ASSISTANT_BG = "#1f2937" # Dark slate for assistant responses
BUBBLE_SYSTEM_BG = "#7c2d12"    # Muted orange/rust for warnings

# Status & indicators
STATUS_SUCCESS = "#10b981"      # Emerald green
STATUS_ERROR = "#ef4444"        # Crimson red
STATUS_WARNING = "#f59e0b"      # Warm amber
STATUS_THINKING = "#3b82f6"     # Bright blue
STATUS_LOADING = "#8b5cf6"      # Soft purple

# UI Elements
BUTTON_BG = "#2563eb"           # Button base
BUTTON_HOVER = "#3b82f6"        # Hover highlight
BUTTON_ACTIVE = "#1d4ed8"       # Active state
BUTTON_TEXT = TEXT_PRIMARY

SCROLLBAR_BG = BG_SECONDARY
SCROLLBAR_THUMB = "#4b5563"     # Neutral gray thumb (Gray 600)

BORDER_COLOR = "#374151"        # Subtle slate borders (Gray 700)
SEPARATOR_COLOR = "#1f2937"

# ============================================================================
# FONTS (Using system font stacks)
# ============================================================================

FONT_FAMILY = "Segoe UI"

# Font sizes (in points)
FONT_SIZE_TITLE = 16
FONT_SIZE_HEADING = 12
FONT_SIZE_BODY = 10
FONT_SIZE_SMALL = 9
FONT_SIZE_TINY = 8

# Font styles
FONT_TITLE = (FONT_FAMILY, FONT_SIZE_TITLE, "bold")
FONT_HEADING = (FONT_FAMILY, FONT_SIZE_HEADING, "bold")
FONT_BODY = (FONT_FAMILY, FONT_SIZE_BODY)
FONT_BODY_BOLD = (FONT_FAMILY, FONT_SIZE_BODY, "bold")
FONT_SMALL = (FONT_FAMILY, FONT_SIZE_SMALL)
FONT_SMALL_BOLD = (FONT_FAMILY, FONT_SIZE_SMALL, "bold")
FONT_TINY = (FONT_FAMILY, FONT_SIZE_TINY)
FONT_MONOSPACE = ("Consolas", FONT_SIZE_BODY)

# ============================================================================
# DIMENSIONS
# ============================================================================

# Spacing (highly consistent padding scale)
PADDING_SMALL = 6
PADDING_NORMAL = 10
PADDING_MEDIUM = 14
PADDING_LARGE = 20

# Sizes
SIDEBAR_WIDTH = 260
INPUT_HEIGHT = 85
STATUS_BAR_HEIGHT = 32
BUTTON_HEIGHT = 32
BUTTON_WIDTH = 90

# Border radius
RADIUS_SMALL = 6
RADIUS_NORMAL = 10
RADIUS_LARGE = 14

# ============================================================================
# ANIMATIONS
# ============================================================================

ANIMATION_DURATION_FAST = 150      # milliseconds
ANIMATION_DURATION_NORMAL = 250
ANIMATION_DURATION_SLOW = 400

# ============================================================================
# WINDOW
# ============================================================================

WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 650
WINDOW_DEFAULT_WIDTH = 1150
WINDOW_DEFAULT_HEIGHT = 750

