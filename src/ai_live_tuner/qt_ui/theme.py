"""Professional dark theme for AI Live Tuner Qt UI."""

# Color constants
C_BG = "#0d0f14"
C_SURFACE = "#141720"
C_CARD = "#1a1e2a"
C_CARD_BORDER = "#252a3a"
C_ACCENT = "#6366f1"
C_ACCENT_HOVER = "#818cf8"
C_ACCENT_PRESSED = "#4f46e5"
C_TEXT = "#e8eaf0"
C_TEXT_DIM = "#8b93a8"
C_TEXT_MUTED = "#505670"
C_GREEN = "#22c55e"
C_YELLOW = "#eab308"
C_RED = "#ef4444"
C_INPUT_BG = "#10131a"

# QSS stylesheet
STYLESHEET = f"""
QMainWindow {{
    background-color: {C_BG};
}}
QWidget {{
    color: {C_TEXT};
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QTabWidget::pane {{
    background: {C_SURFACE};
    border: 1px solid {C_CARD_BORDER};
    border-radius: 6px;
}}
QTabBar::tab {{
    background: {C_CARD};
    color: {C_TEXT_DIM};
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background: {C_ACCENT};
    color: white;
}}
QTabBar::tab:hover:!selected {{
    background: {C_CARD_BORDER};
}}
QGroupBox {{
    background: {C_CARD};
    border: 1px solid {C_CARD_BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 6px;
    color: {C_TEXT};
}}
QLabel {{
    color: {C_TEXT};
    background: transparent;
}}
QLabel[dim="true"] {{
    color: {C_TEXT_DIM};
}}
QLabel[muted="true"] {{
    color: {C_TEXT_MUTED};
}}
QPushButton {{
    background: {C_INPUT_BG};
    color: {C_TEXT};
    border: 1px solid {C_CARD_BORDER};
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
}}
QPushButton:hover {{
    background: {C_CARD_BORDER};
    border-color: {C_ACCENT};
}}
QPushButton:pressed {{
    background: {C_ACCENT_PRESSED};
}}
QPushButton[accent="true"] {{
    background: {C_ACCENT};
    color: white;
    border: none;
    font-weight: bold;
}}
QPushButton[accent="true"]:hover {{
    background: {C_ACCENT_HOVER};
}}
QPushButton[accent="true"]:pressed {{
    background: {C_ACCENT_PRESSED};
}}
QComboBox {{
    background: {C_INPUT_BG};
    color: {C_TEXT};
    border: 1px solid {C_CARD_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 120px;
}}
QComboBox:hover {{
    border-color: {C_ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background: {C_CARD};
    color: {C_TEXT};
    border: 1px solid {C_CARD_BORDER};
    selection-background-color: {C_ACCENT};
}}
QSlider::groove:horizontal {{
    background: {C_CARD_BORDER};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {C_ACCENT};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {C_ACCENT_HOVER};
}}
QSlider::sub-page:horizontal {{
    background: {C_ACCENT};
    border-radius: 3px;
}}
QCheckBox {{
    color: {C_TEXT};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {C_CARD_BORDER};
    border-radius: 4px;
    background: {C_INPUT_BG};
}}
QCheckBox::indicator:checked {{
    background: {C_ACCENT};
    border-color: {C_ACCENT};
}}
QLineEdit {{
    background: {C_INPUT_BG};
    color: {C_TEXT};
    border: 1px solid {C_CARD_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
}}
QLineEdit:focus {{
    border-color: {C_ACCENT};
}}
QStatusBar {{
    background: {C_SURFACE};
    color: {C_TEXT_DIM};
    border-top: 1px solid {C_CARD_BORDER};
}}
"""
