"""Effect test tab for recording and A/B comparison."""

from __future__ import annotations

import tkinter as tk

from .theme import C_BG, C_CARD, C_TEXT, C_TEXT_MUTED, FONT_BODY, FONT_MONO
from .widgets import Card, StyledButton


class TestTab(tk.Frame):
    """Effect test tab: record 5 seconds, compare original vs processed."""

    def __init__(self, master: tk.Widget, app: object) -> None:
        super().__init__(master, bg=C_BG)
        self.app = app
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        card = Card(self, "录音对比测试")
        card.grid(row=0, column=0, sticky="new")

        tk.Label(card.inner, text="录 5 秒人声，软件会用当前参数生成处理后版本。对比原声和修音效果，再决定是否用于直播。",
                 bg=C_CARD, fg=C_TEXT_MUTED, font=FONT_BODY,
                 wraplength=760).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))

        tk.Label(card.inner, textvariable=self.app.test_status_var, bg=C_CARD, fg=C_TEXT,
                 font=FONT_MONO).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 12))

        btn_row = tk.Frame(card.inner, bg=C_CARD)
        btn_row.grid(row=2, column=0, columnspan=4, sticky="w")
        StyledButton(btn_row, "录制 5 秒", self.app.record_effect_test, accent=True).pack(side="left")
        StyledButton(btn_row, "播放原声", lambda: self.app.play_test_audio("original")).pack(
            side="left", padx=(10, 0))
        StyledButton(btn_row, "播放处理后", lambda: self.app.play_test_audio("processed")).pack(
            side="left", padx=(10, 0))
        StyledButton(btn_row, "A/B 连续对比", self.app.play_ab_test).pack(side="left", padx=(10, 0))
