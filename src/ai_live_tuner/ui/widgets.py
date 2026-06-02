"""Custom Canvas widgets for the AI Live Tuner UI."""

from __future__ import annotations

import tkinter as tk

import numpy as np

from .theme import (
    C_ACCENT,
    C_BG,
    C_CARD,
    C_CARD_BORDER,
    C_GREEN,
    C_INPUT_BG,
    C_RED,
    C_TEXT,
    C_TEXT_DIM,
    C_TEXT_MUTED,
    C_YELLOW,
    FONT_GAUGE_FREQ,
    FONT_GAUGE_NOTE,
    FONT_MONO_TINY,
    PEAK_DECAY_RATE,
    PEAK_DECAY_SPEED,
    SMOOTH_GAUGE,
    SMOOTH_LEVEL,
    SMOOTH_SPECTRUM,
)


def _lerp_color(t: float) -> str:
    """Gradient from green -> yellow -> red based on t in [0, 1]."""
    if t < 0.6:
        return C_GREEN
    if t < 0.85:
        return C_YELLOW
    return C_RED


class LevelMeter(tk.Canvas):
    """Vertical level meter with gradient colors and peak hold."""

    def __init__(self, master: tk.Widget, width: int = 28, height: int = 200) -> None:
        super().__init__(master, bg=C_CARD, highlightthickness=0)
        self.configure(width=width, height=height)
        self._level = 0.0
        self._peak = 0.0
        self._peak_decay = 0.0
        self._target_level = 0.0
        self._cw = width
        self._ch = height

    def set_level(self, value: float) -> None:
        self._target_level = float(np.clip(value, 0.0, 1.0))

    def animate(self) -> None:
        self._level += (self._target_level - self._level) * SMOOTH_LEVEL
        if self._level > self._peak:
            self._peak = self._level
            self._peak_decay = 0.0
        else:
            self._peak_decay += PEAK_DECAY_RATE
            self._peak = max(0.0, self._peak - self._peak_decay * PEAK_DECAY_SPEED)

        self.delete("all")
        w, h = self._cw, self._ch
        bar_w = w - 8
        bar_h = h - 16
        x0, y0 = 4, 8

        # background track
        self.create_rectangle(x0, y0, x0 + bar_w, y0 + bar_h, fill=C_INPUT_BG, outline="")

        # level bar with gradient
        fill_h = int(bar_h * self._level)
        if fill_h > 1:
            y1 = y0 + bar_h - fill_h
            seg_h = max(1, bar_h // 20)
            for i in range(0, fill_h, seg_h):
                y = y0 + bar_h - i - seg_h
                ratio = i / max(bar_h, 1)
                color = _lerp_color(ratio)
                self.create_rectangle(x0, max(y, y1), x0 + bar_w, y + seg_h, fill=color, outline="")

        # peak indicator
        if self._peak > 0.02:
            peak_y = y0 + bar_h - int(bar_h * self._peak)
            self.create_line(x0, peak_y, x0 + bar_w, peak_y, fill=C_TEXT, width=2)

        # scale marks
        for pct in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = y0 + bar_h - int(bar_h * pct)
            self.create_line(x0 + bar_w + 1, y, x0 + bar_w + 4, y, fill=C_TEXT_MUTED, width=1)


class PitchGauge(tk.Canvas):
    """Semi-circular gauge showing pitch deviation in cents."""

    def __init__(self, master: tk.Widget, size: int = 180) -> None:
        super().__init__(master, bg=C_CARD, highlightthickness=0)
        self.configure(width=size, height=size // 2 + 30)
        self._size = size
        self._cents = 0.0
        self._target_cents = 0.0
        self._note_name = "--"
        self._frequency = 0.0

    def set_values(self, cents: float, note_name: str, frequency: float) -> None:
        self._target_cents = float(np.clip(cents, -100.0, 100.0))
        self._note_name = note_name
        self._frequency = frequency

    def animate(self) -> None:
        self._cents += (self._target_cents - self._cents) * SMOOTH_GAUGE

        self.delete("all")
        s = self._size
        cx, cy = s // 2, s // 2 + 10
        r = s // 2 - 20

        # arc segments
        for i in range(-50, 51, 5):
            angle_start = 210 - (i + 50) * 240 / 100
            angle_end = 210 - (i + 50 + 5) * 240 / 100
            if abs(i) < 15:
                color = C_GREEN
            elif abs(i) < 35:
                color = C_YELLOW
            else:
                color = C_RED
            self.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=angle_start, extent=angle_end - angle_start,
                style="arc", width=6, outline=color,
            )

        # tick marks
        for cent in [-50, -25, 0, 25, 50]:
            angle = 210 - (cent + 50) * 240 / 100
            rad = angle * 3.14159 / 180
            x1 = cx + (r - 12) * np.cos(rad)
            y1 = cy - (r - 12) * np.sin(rad)
            x2 = cx + (r + 2) * np.cos(rad)
            y2 = cy - (r + 2) * np.sin(rad)
            self.create_line(x1, y1, x2, y2, fill=C_TEXT_MUTED, width=2)

        # needle
        angle = 210 - (self._cents + 50) * 240 / 100
        rad = angle * 3.14159 / 180
        nx = cx + (r - 20) * np.cos(rad)
        ny = cy - (r - 20) * np.sin(rad)
        self.create_line(cx, cy, nx, ny, fill=C_TEXT, width=3, capstyle="round")
        self.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=C_ACCENT, outline="")

        # note name
        self.create_text(cx, cy - 18, text=self._note_name, fill=C_TEXT,
                         font=FONT_GAUGE_NOTE, anchor="s")
        # frequency
        if self._frequency > 0:
            self.create_text(cx, cy + 4, text=f"{self._frequency:.0f} Hz", fill=C_TEXT_DIM,
                             font=FONT_GAUGE_FREQ, anchor="n")
        # cents label
        sign = "+" if self._cents >= 0 else ""
        self.create_text(cx, cy + 22, text=f"{sign}{self._cents:.0f} ct", fill=C_TEXT_MUTED,
                         font=FONT_MONO_TINY, anchor="n")


class SpectrumDisplay(tk.Canvas):
    """Simple spectrum bar visualization."""

    def __init__(self, master: tk.Widget, canvas_width: int = 400, canvas_height: int = 80) -> None:
        super().__init__(master, bg=C_CARD, highlightthickness=0)
        self._cw = canvas_width
        self._ch = canvas_height
        self._bars = np.zeros(32, dtype=np.float32)
        self._target_bars = np.zeros(32, dtype=np.float32)

    def set_spectrum(self, spectrum: np.ndarray) -> None:
        if spectrum.size < 1:
            return
        n = self._target_bars.size
        chunk = max(1, spectrum.size // n)
        for i in range(n):
            start = i * chunk
            end = min(start + chunk, spectrum.size)
            self._target_bars[i] = float(np.mean(spectrum[start:end]))

    def animate(self) -> None:
        self._bars += (self._target_bars - self._bars) * SMOOTH_SPECTRUM

        self.delete("all")
        w, h = self._cw, self._ch
        n = self._bars.size
        bar_w = max(2, (w - 4) // n - 1)
        gap = 1
        max_val = max(float(np.max(self._bars)), 0.01)

        for i in range(n):
            val = self._bars[i] / max_val
            bar_h = max(1, int(val * (h - 8)))
            x = 2 + i * (bar_w + gap)
            y = h - 4 - bar_h
            color = _lerp_color(val)
            self.create_rectangle(x, y, x + bar_w, h - 4, fill=color, outline="")


class Card(tk.Frame):
    """A card-like frame with title, matching the dark theme.

    After creating the card, call .pack() or .grid() on the card itself
    to place it on the parent. Use .inner to add child widgets.
    """

    def __init__(self, master: tk.Widget, title: str = "", **kwargs: object) -> None:
        super().__init__(master, bg=C_CARD, highlightbackground=C_CARD_BORDER,
                         highlightthickness=1, **kwargs)
        if title:
            tk.Label(self, text=title, bg=C_CARD, fg=C_TEXT,
                     font=("Microsoft YaHei UI", 10, "bold"), anchor="w").pack(
                fill="x", padx=PAD, pady=(12, 4))
        self.inner = tk.Frame(self, bg=C_CARD)
        self.inner.pack(fill="both", expand=True, padx=PAD, pady=(0, 12))


PAD = 16


class StyledButton(tk.Button):
    """Button matching the dark theme."""

    def __init__(self, master: tk.Widget, text: str, command: object,
                 accent: bool = False, **kwargs: object) -> None:
        from .theme import C_ACCENT, C_ACCENT_HOVER, C_INPUT_BG, C_TEXT
        bg = C_ACCENT if accent else C_INPUT_BG
        fg = "#ffffff" if accent else C_TEXT
        font = ("Microsoft YaHei UI", 11, "bold") if accent else ("Microsoft YaHei UI", 10)
        super().__init__(master, text=text, command=command, bg=bg, fg=fg,
                         font=font, relief="flat", padx=16, pady=7,
                         activebackground=C_ACCENT_HOVER, activeforeground="#ffffff",
                         cursor="hand2", **kwargs)
        self._bg = bg
        self._accent = accent
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event: object) -> None:
        from .theme import C_ACCENT_HOVER
        self.configure(bg=C_ACCENT_HOVER)

    def _on_leave(self, _event: object) -> None:
        self.configure(bg=self._bg)
