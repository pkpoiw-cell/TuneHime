"""Custom Qt widgets for AI Live Tuner."""

from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal as Signal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .theme import (
    C_ACCENT,
    C_CARD,
    C_CARD_BORDER,
    C_GREEN,
    C_RED,
    C_TEXT,
    C_TEXT_DIM,
    C_TEXT_MUTED,
    C_YELLOW,
)


class LevelMeter(QWidget):
    """Vertical VU meter with peak hold."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(36, 200)
        self._level = 0.0
        self._target = 0.0
        self._peak = 0.0
        self._peak_decay = 0.0

    def set_level(self, value: float) -> None:
        self._target = max(0.0, min(1.0, value))

    def tick(self) -> None:
        self._level += (self._target - self._level) * 0.35
        if self._level > self._peak:
            self._peak = self._level
            self._peak_decay = 0.0
        else:
            self._peak_decay += 0.015
            self._peak = max(0.0, self._peak - self._peak_decay * 0.08)
        self.update()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        bar_w = w - 12
        bar_h = h - 20
        x0, y0 = 6, 10

        # background track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#10131a"))
        p.drawRoundedRect(x0, y0, bar_w, bar_h, 3, 3)

        # level bar
        fill_h = int(bar_h * self._level)
        if fill_h > 1:
            y1 = y0 + bar_h - fill_h
            seg_h = max(1, bar_h // 24)
            for i in range(0, fill_h, seg_h):
                y = y0 + bar_h - i - seg_h
                ratio = i / max(bar_h, 1)
                if ratio < 0.6:
                    color = QColor(C_GREEN)
                elif ratio < 0.85:
                    color = QColor(C_YELLOW)
                else:
                    color = QColor(C_RED)
                p.setBrush(color)
                p.drawRect(x0, max(y, y1), bar_w, seg_h)

        # peak indicator
        if self._peak > 0.02:
            peak_y = y0 + bar_h - int(bar_h * self._peak)
            p.setPen(QPen(QColor(C_TEXT), 2))
            p.drawLine(x0, peak_y, x0 + bar_w, peak_y)

        # scale marks
        p.setPen(QPen(QColor(C_TEXT_MUTED), 1))
        for pct in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = y0 + bar_h - int(bar_h * pct)
            p.drawLine(x0 + bar_w + 2, y, x0 + bar_w + 5, y)

        p.end()


class PitchGauge(QWidget):
    """Arc gauge showing pitch deviation in cents."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(200, 130)
        self._cents = 0.0
        self._target_cents = 0.0
        self._note = "--"
        self._freq = 0.0

    def set_values(self, cents: float, note: str, freq: float) -> None:
        self._target_cents = max(-100.0, min(100.0, cents))
        self._note = note
        self._freq = freq

    def tick(self) -> None:
        self._cents += (self._target_cents - self._cents) * 0.25
        self.update()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h - 15
        r = max(10, min(w, h * 2) // 2 - 25)

        # arc segments
        for i in range(-50, 51, 5):
            angle_start = 180 + (i + 50) * 180 / 100
            angle_end = 180 + (i + 50 + 5) * 180 / 100
            if abs(i) < 15:
                color = QColor(C_GREEN)
            elif abs(i) < 35:
                color = QColor(C_YELLOW)
            else:
                color = QColor(C_RED)
            p.setPen(QPen(color, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(cx - r, cy - r, r * 2, r * 2,
                      int(angle_start * 16), int((angle_end - angle_start) * 16))

        # tick marks
        p.setPen(QPen(QColor(C_TEXT_MUTED), 2))
        for cent in (-50, -25, 0, 25, 50):
            angle = math.radians(180 + (cent + 50) * 180 / 100)
            x1 = cx + (r - 10) * math.cos(angle)
            y1 = cy - (r - 10) * math.sin(angle)
            x2 = cx + (r + 3) * math.cos(angle)
            y2 = cy - (r + 3) * math.sin(angle)
            p.drawLine(int(x1), int(y1), int(x2), int(y2))

        # needle
        angle = math.radians(180 + (self._cents + 50) * 180 / 100)
        nx = cx + (r - 18) * math.cos(angle)
        ny = cy - (r - 18) * math.sin(angle)
        p.setPen(QPen(QColor(C_TEXT), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(cx, cy, int(nx), int(ny))

        # center dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C_ACCENT))
        p.drawEllipse(cx - 5, cy - 5, 10, 10)

        from PyQt6.QtCore import QRect
        # note name
        p.setPen(QColor(C_TEXT))
        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.drawText(QRect(cx - 60, cy - 40, 120, 30), Qt.AlignmentFlag.AlignCenter, self._note)

        # frequency
        if self._freq > 0:
            p.setPen(QColor(C_TEXT_DIM))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(QRect(cx - 60, cy + 2, 120, 16), Qt.AlignmentFlag.AlignCenter, f"{self._freq:.0f} Hz")

        # cents
        sign = "+" if self._cents >= 0 else ""
        p.setPen(QColor(C_TEXT_MUTED))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(QRect(cx - 60, cy + 18, 120, 14), Qt.AlignmentFlag.AlignCenter, f"{sign}{self._cents:.0f} ct")

        p.end()


class SpectrumDisplay(QWidget):
    """Bar spectrum visualization."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 70)
        self._bars = np.zeros(32, dtype=np.float32)
        self._target = np.zeros(32, dtype=np.float32)

    def set_spectrum(self, spectrum: np.ndarray) -> None:
        if spectrum.size < 1:
            return
        n = self._target.size
        chunk = max(1, spectrum.size // n)
        for i in range(n):
            s = i * chunk
            e = min(s + chunk, spectrum.size)
            self._target[i] = float(np.mean(spectrum[s:e]))

    def tick(self) -> None:
        self._bars += (self._target - self._bars) * 0.30
        self.update()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        n = self._bars.size
        bar_w = max(2, (w - 4) // n - 1)
        gap = 1
        max_val = max(float(np.max(self._bars)), 0.01)

        for i in range(n):
            val = self._bars[i] / max_val
            bar_h = max(1, int(val * (h - 8)))
            x = 2 + i * (bar_w + gap)
            y = h - 4 - bar_h

            if val < 0.5:
                color = QColor(C_GREEN)
            elif val < 0.8:
                color = QColor(C_YELLOW)
            else:
                color = QColor(C_RED)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(x, y, bar_w, bar_h, 1, 1)

        p.end()


class ParamSlider(QWidget):
    """Labeled slider with value display."""

    valueChanged = Signal(float)

    def __init__(self, label: str, min_val: float = 0.0, max_val: float = 1.0,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._min = min_val
        self._max = max_val

        from PyQt6.QtWidgets import QHBoxLayout, QSlider
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        self._label = QLabel(label)
        self._label.setProperty("dim", True)
        self._label.setFixedWidth(70)
        layout.addWidget(self._label)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(int((0.5 - min_val) / (max_val - min_val) * 1000))
        self._slider.valueChanged.connect(self._on_change)
        layout.addWidget(self._slider, 1)

        self._value_label = QLabel("0.50")
        self._value_label.setFixedWidth(45)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._value_label)

    def _on_change(self, raw: int) -> None:
        val = self._min + (raw / 1000.0) * (self._max - self._min)
        self._value_label.setText(f"{val:.2f}")
        self.valueChanged.emit(val)

    def value(self) -> float:
        return self._min + (self._slider.value() / 1000.0) * (self._max - self._min)

    def set_value(self, val: float) -> None:
        raw = int((val - self._min) / (self._max - self._min) * 1000)
        self._slider.setValue(max(0, min(1000, raw)))
