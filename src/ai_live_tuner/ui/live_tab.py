"""One-click live streaming tab."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import numpy as np

from .theme import (
    C_ACCENT,
    C_BG,
    C_CARD,
    C_CARD_BORDER,
    C_INPUT_BG,
    C_TEXT,
    C_TEXT_DIM,
    C_TEXT_MUTED,
    FONT_BODY,
    FONT_HEADING,
    FONT_MONO,
    FONT_SMALL,
    PAD_INNER,
    PAD_TINY,
)
from .widgets import LevelMeter, PitchGauge, SpectrumDisplay, Card, StyledButton


class LiveTab(tk.Frame):
    """One-click live tab with device selection, auto mode, and visualization."""

    def __init__(self, master: tk.Widget, app: object) -> None:
        super().__init__(master, bg=C_BG)
        self.app = app
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(1, weight=1)

        # left column: controls
        left = tk.Frame(self, bg=C_BG)
        left.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)

        # device selection
        dev_card = Card(left, "设备选择")
        dev_card.pack(fill="x", pady=(0, 12))

        tk.Label(dev_card.inner, text="输入", bg=C_CARD, fg=C_TEXT_DIM, font=FONT_SMALL).grid(
            row=0, column=0, sticky="w", pady=PAD_TINY)
        self.input_combo = ttk.Combobox(dev_card.inner, textvariable=self.app.input_var,
                                         state="readonly", width=36)
        self.input_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=PAD_TINY)

        tk.Label(dev_card.inner, text="输出", bg=C_CARD, fg=C_TEXT_DIM, font=FONT_SMALL).grid(
            row=1, column=0, sticky="w", pady=PAD_TINY)
        self.output_combo = ttk.Combobox(dev_card.inner, textvariable=self.app.output_var,
                                          state="readonly", width=36)
        self.output_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=PAD_TINY)

        StyledButton(dev_card.inner, "刷新", self.app._load_devices).grid(
            row=0, column=2, rowspan=2, padx=(8, 0))
        dev_card.inner.columnconfigure(1, weight=1)

        # auto mode
        auto_card = Card(left, "自动模式")
        auto_card.pack(fill="x", pady=(0, 12))

        tk.Checkbutton(auto_card.inner, text="自动识别调号并自动调参",
                        variable=self.app.auto_mode_var, bg=C_CARD, fg=C_TEXT,
                        selectcolor=C_INPUT_BG, activebackground=C_CARD,
                        activeforeground=C_TEXT, font=FONT_BODY).pack(anchor="w", pady=(0, 8))
        tk.Label(auto_card.inner, textvariable=self.app.auto_status_var,
                 bg=C_CARD, fg=C_ACCENT, font=FONT_BODY).pack(anchor="w", pady=(4, 12))

        btn_frame = tk.Frame(auto_card.inner, bg=C_CARD)
        btn_frame.pack(fill="x")
        StyledButton(btn_frame, "一键开始直播修音", self.app.one_click_start, accent=True).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        StyledButton(btn_frame, "停止", self.app.stop_audio).pack(side="right")

        # realtime feedback
        mon_card = Card(left, "实时反馈")
        mon_card.pack(fill="x", pady=(0, 12))

        for i, (label_text, var) in enumerate([
            ("检测音高", self.app.pitch_label_var),
            ("目标音", self.app.target_label_var),
            ("修正量", self.app.shift_label_var),
        ]):
            tk.Label(mon_card.inner, text=label_text, bg=C_CARD, fg=C_TEXT_MUTED,
                     font=FONT_SMALL).grid(row=i, column=0, sticky="w", pady=2)
            tk.Label(mon_card.inner, textvariable=var, bg=C_CARD, fg=C_TEXT,
                     font=FONT_MONO).grid(row=i, column=1, sticky="w", padx=(12, 0), pady=2)

        # spectrum
        spec_card = Card(left, "频谱")
        spec_card.pack(fill="x")
        self.spectrum_display = SpectrumDisplay(spec_card.inner, canvas_width=480, canvas_height=70)
        self.spectrum_display.pack(fill="x")

        # right column: gauges
        right = tk.Frame(self, bg=C_BG)
        right.grid(row=0, column=1, rowspan=2, sticky="n", padx=(12, 0))

        gauge_card = Card(right, "音高偏差")
        gauge_card.pack(fill="x", pady=(0, 12))
        self.pitch_gauge = PitchGauge(gauge_card.inner, size=200)
        self.pitch_gauge.pack()

        level_card = Card(right, "输出音量")
        level_card.pack(fill="x")
        self.level_meter = LevelMeter(level_card.inner, width=32, height=220)
        self.level_meter.pack()
