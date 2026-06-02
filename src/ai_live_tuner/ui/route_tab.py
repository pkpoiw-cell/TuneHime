"""Virtual sound card routing tab."""

from __future__ import annotations

import tkinter as tk

from .theme import C_BG, C_CARD, C_TEXT, C_TEXT_DIM, C_TEXT_MUTED, FONT_BODY, FONT_MONO
from .widgets import Card, StyledButton


class RouteTab(tk.Frame):
    """Virtual sound card tab for routing to OBS/livestream software."""

    def __init__(self, master: tk.Widget, app: object) -> None:
        super().__init__(master, bg=C_BG)
        self.app = app
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        card = Card(self, "虚拟声卡模式")
        card.grid(row=0, column=0, sticky="new", pady=(0, 12))

        tk.Label(card.inner, text="选择 CABLE Input / Voicemeeter Input 后，直播软件选择对应 Output，获得类似虚拟麦克风的路由效果。",
                 bg=C_CARD, fg=C_TEXT_MUTED, font=FONT_BODY,
                 wraplength=760).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        tk.Label(card.inner, textvariable=self.app.route_status_var, bg=C_CARD, fg=C_TEXT,
                 font=FONT_MONO).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        btn_row = tk.Frame(card.inner, bg=C_CARD)
        btn_row.grid(row=2, column=0, columnspan=3, sticky="w")
        StyledButton(btn_row, "自动查找虚拟声卡", self.app.select_virtual_output, accent=True).pack(side="left")
        StyledButton(btn_row, "发送 1 秒测试音", self.app.play_route_test_tone).pack(side="left", padx=(10, 0))
        StyledButton(btn_row, "刷新设备", self.app._load_devices).pack(side="left", padx=(10, 0))

        # steps card
        steps_card = Card(self, "直播软件设置")
        steps_card.grid(row=1, column=0, sticky="new")

        steps = (
            '1. 本软件"输出"选择 CABLE Input\n'
            '2. OBS/直播伴侣"麦克风"选择 CABLE Output\n'
            '3. 点击"发送 1 秒测试音"，在直播软件音量条看到跳动即可\n'
            '4. 回到"一键直播"，点击"一键开始直播修音"'
        )
        tk.Label(steps_card.inner, text=steps, bg=C_CARD, fg=C_TEXT_DIM,
                 font=FONT_BODY, justify="left", wraplength=760).pack(anchor="w")
