"""Advanced settings tab."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import (
    C_BG,
    C_CARD,
    C_CARD_BORDER,
    C_INPUT_BG,
    C_SLIDER_TROUGH,
    C_TEXT,
    C_TEXT_DIM,
    C_TEXT_MUTED,
    FONT_BODY,
    FONT_SMALL,
)
from .widgets import Card, StyledButton


SCALE_LABELS = ("大调", "小调", "半音阶")


class SettingsTab(tk.Frame):
    """Advanced settings tab with presets, tuning, and voice processing."""

    def __init__(self, master: tk.Widget, app: object) -> None:
        super().__init__(master, bg=C_BG)
        self.app = app
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        # preset bar
        preset_frame = tk.Frame(self, bg=C_BG)
        preset_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        tk.Label(preset_frame, text="预设", bg=C_BG, fg=C_TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(
            side="left", padx=(0, 10))
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.app.preset_var,
                                          values=tuple(self.app.presets.keys()), state="readonly", width=14)
        self.preset_combo.pack(side="left")
        StyledButton(preset_frame, "应用", self.app.apply_preset, accent=True).pack(side="left", padx=(10, 0))
        StyledButton(preset_frame, "保存为新预设", self.app.save_current_preset).pack(side="left", padx=(10, 0))
        StyledButton(preset_frame, "删除预设", self.app.delete_current_preset).pack(side="left", padx=(10, 0))

        from ai_live_tuner.dsp import NOTE_NAMES

        # tuning card
        tuning_card = Card(self, "修音")
        tuning_card.grid(row=2, column=0, sticky="nsew", pady=(0, 12), padx=(0, 6))

        tk.Label(tuning_card.inner, text="调号", bg=C_CARD, fg=C_TEXT_DIM, font=FONT_SMALL).grid(
            row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(tuning_card.inner, textvariable=self.app.root_var, values=NOTE_NAMES,
                     state="readonly", width=10).grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))

        tk.Label(tuning_card.inner, text="调式", bg=C_CARD, fg=C_TEXT_DIM, font=FONT_SMALL).grid(
            row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(tuning_card.inner, textvariable=self.app.scale_var, values=SCALE_LABELS,
                     state="readonly", width=10).grid(row=1, column=1, sticky="ew", pady=4, padx=(8, 0))
        StyledButton(tuning_card.inner, "智能识别", self.app.smart_detect_key).grid(row=1, column=2, padx=(8, 0))

        for i, (label, var, lo, hi) in enumerate([
            ("修音强度", self.app.amount_var, 0.0, 1.0),
            ("修音速度", self.app.speed_var, 0.01, 1.0),
            ("干湿比", self.app.mix_var, 0.0, 1.0),
        ], start=2):
            self._styled_slider(tuning_card.inner, label, var, lo, hi, row=i)

        tk.Checkbutton(tuning_card.inner, text="自动模式覆盖参数", variable=self.app.auto_mode_var,
                        bg=C_CARD, fg=C_TEXT_DIM, selectcolor=C_INPUT_BG,
                        activebackground=C_CARD).grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))
        tuning_card.inner.columnconfigure(1, weight=1)

        # output card
        output_card = Card(self, "监听与输出")
        output_card.grid(row=2, column=1, sticky="nsew", pady=(0, 12), padx=(6, 0))

        self._styled_slider(output_card.inner, "增益", self.app.gain_var, 0.2, 2.0, row=0)

        tk.Checkbutton(output_card.inner, text="旁路修音", variable=self.app.bypass_var,
                        bg=C_CARD, fg=C_TEXT_DIM, selectcolor=C_INPUT_BG,
                        activebackground=C_CARD).grid(row=1, column=0, columnspan=3, sticky="w", pady=6)

        for i, (label, var) in enumerate([
            ("检测音高", self.app.pitch_label_var),
            ("目标音", self.app.target_label_var),
            ("修正量", self.app.shift_label_var),
        ], start=2):
            tk.Label(output_card.inner, text=label, bg=C_CARD, fg=C_TEXT_MUTED,
                     font=FONT_SMALL).grid(row=i, column=0, sticky="w", pady=2)
            tk.Label(output_card.inner, textvariable=var, bg=C_CARD, fg=C_TEXT,
                     font=("Segoe UI", 12, "bold")).grid(row=i, column=1, sticky="w", padx=(8, 0), pady=2)
        output_card.inner.columnconfigure(1, weight=1)

        # voice processing card
        voice_card = Card(self, "人声处理")
        voice_card.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        params = [
            ("噪声门", self.app.gate_var, 0.0, 1.0),
            ("压缩", self.app.compression_var, 0.0, 1.0),
            ("亮度", self.app.brightness_var, 0.0, 1.0),
            ("齿音消除", self.app.deesser_var, 0.0, 1.0),
            ("混响", self.app.reverb_var, 0.0, 1.0),
        ]
        for i, (label, var, lo, hi) in enumerate(params):
            col = i % 3
            row = i // 3
            self._styled_slider(voice_card.inner, label, var, lo, hi, row=row, column=col * 3)
        voice_card.inner.columnconfigure(1, weight=1)
        voice_card.inner.columnconfigure(4, weight=1)
        voice_card.inner.columnconfigure(7, weight=1)

        # buttons
        btn_bar = tk.Frame(self, bg=C_BG)
        btn_bar.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        StyledButton(btn_bar, "开始直播处理", self.app.start_audio, accent=True).pack(side="left")
        StyledButton(btn_bar, "停止", self.app.stop_audio).pack(side="left", padx=10)
        StyledButton(btn_bar, "打开目录", self.app._show_folder).pack(side="right")

    def _styled_slider(self, parent: tk.Frame, label: str, var: object,
                       start: float, end: float, row: int, column: int = 0) -> None:
        tk.Label(parent, text=label, bg=C_CARD, fg=C_TEXT_DIM,
                 font=FONT_SMALL).grid(row=row, column=column, sticky="w", pady=4)
        slider = tk.Scale(parent, variable=var, from_=start, to=end, orient="horizontal",
                          bg=C_CARD, fg=C_TEXT, troughcolor=C_SLIDER_TROUGH,
                          highlightthickness=0, sliderrelief="flat", length=160,
                          showvalue=False, activebackground=C_CARD_BORDER)
        slider.grid(row=row, column=column + 1, sticky="ew", padx=(8, 4), pady=4)
        val_label = tk.Label(parent, text=f"{var.get():.2f}", bg=C_CARD, fg=C_TEXT,
                             font=FONT_MONO_SMALL, width=5)
        val_label.grid(row=row, column=column + 2, sticky="e", pady=4)

        def refresh(*_: object) -> None:
            val_label.configure(text=f"{var.get():.2f}")

        var.trace_add("write", refresh)
        parent.columnconfigure(column + 1, weight=1)


FONT_MONO_SMALL = ("Segoe UI", 10)
