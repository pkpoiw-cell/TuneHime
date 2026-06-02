"""Professional dark theme for AI Live Tuner.

Color palette inspired by iZotope / FL Studio dark theme.
"""

# ---------------------------------------------------------------------------
# Color palette — deep indigo-charcoal
# ---------------------------------------------------------------------------
C_BG = "#0f1117"
C_SURFACE = "#181b24"
C_CARD = "#1e2230"
C_CARD_HOVER = "#252938"
C_CARD_BORDER = "#2a2f42"
C_ACCENT = "#6366f1"
C_ACCENT_HOVER = "#818cf8"
C_ACCENT_DIM = "#4f46e5"
C_TEXT = "#e8eaf0"
C_TEXT_DIM = "#9ca3b4"
C_TEXT_MUTED = "#5f6578"
C_SUCCESS = "#22c55e"
C_WARNING = "#f59e0b"
C_DANGER = "#ef4444"
C_INPUT_BG = "#161922"
C_SLIDER_TROUGH = "#2a2f42"
C_GREEN = "#22c55e"
C_YELLOW = "#eab308"
C_RED = "#ef4444"

# Gradient stops for level meter
METER_COLORS = [
    (0.0, "#22c55e"),   # green
    (0.6, "#22c55e"),
    (0.75, "#eab308"),  # yellow
    (0.9, "#ef4444"),   # red
    (1.0, "#ef4444"),
]

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
FONT_TITLE = ("Microsoft YaHei UI", 24, "bold")
FONT_SUBTITLE = ("Microsoft YaHei UI", 10)
FONT_HEADING = ("Microsoft YaHei UI", 10, "bold")
FONT_BODY = ("Microsoft YaHei UI", 10)
FONT_SMALL = ("Microsoft YaHei UI", 9)
FONT_TINY = ("Microsoft YaHei UI", 8)
FONT_MONO = ("Segoe UI", 14, "bold")
FONT_MONO_SMALL = ("Segoe UI", 10)
FONT_MONO_TINY = ("Segoe UI", 8)
FONT_GAUGE_NOTE = ("Segoe UI", 16, "bold")
FONT_GAUGE_FREQ = ("Segoe UI", 10)

# ---------------------------------------------------------------------------
# Spacing
# ---------------------------------------------------------------------------
PAD_OUTER = 20
PAD_CARD = 16
PAD_INNER = 12
PAD_TINY = 4
CORNER_RADIUS = 10

# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------
ANIM_FPS = 60
ANIM_INTERVAL_MS = 16
SMOOTH_LEVEL = 0.35
SMOOTH_GAUGE = 0.25
SMOOTH_SPECTRUM = 0.30
PEAK_DECAY_RATE = 0.015
PEAK_DECAY_SPEED = 0.08
