"""Main window for AI Live Tuner Qt UI."""

from __future__ import annotations

import queue
import threading
from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    import sounddevice as sd
except ImportError:
    sd = None

from .theme import C_ACCENT, C_BG, C_CARD, C_TEXT, C_TEXT_DIM, C_TEXT_MUTED, STYLESHEET
from .widgets import LevelMeter, ParamSlider, PitchGauge, SpectrumDisplay


SAMPLE_RATE = 48000
BLOCK_SIZE = 2048
PITCH_WINDOW = 4096
SCALE_LABELS = {"大调": "major", "小调": "minor", "半音阶": "chromatic"}
SCALE_TO_LABEL = {v: k for k, v in SCALE_LABELS.items()}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI 直播修音")
        self.setMinimumSize(1000, 700)
        self.resize(1100, 780)
        self.setStyleSheet(STYLESHEET)

        # import backend
        from ..audio_engine import RealtimeVoiceEngine, engine_available
        self._engine_available = engine_available
        from ..logging_setup import setup_logging
        from ..settings import DEFAULT_CONFIG, load_state, merged_presets, settings_path

        self.logger = setup_logging()
        self.saved_state = load_state()
        self.user_presets = dict(self.saved_state["presets"])
        self.presets = merged_presets(self.user_presets)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(self.saved_state["config"])

        self.engine = RealtimeVoiceEngine(SAMPLE_RATE, BLOCK_SIZE, PITCH_WINDOW)
        self.status_queue: queue.Queue[dict[str, object]] = queue.Queue(maxsize=8)
        self.stop_event = threading.Event()
        self.audio_thread: threading.Thread | None = None
        self.stream = None
        self.input_devices: list[tuple[str, int | None]] = []
        self.output_devices: list[tuple[str, int | None]] = []

        # config state
        self._cfg = dict(cfg)

        self._build_ui()
        self._load_devices()

        # animation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16)

        # status poll timer
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start(80)

        self.logger.info("Application started; settings=%s", settings_path())

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # header
        header = QHBoxLayout()
        title_frame = QVBoxLayout()
        title = QLabel("AI 直播修音")
        title.setFont(QFont("Microsoft YaHei UI", 24, QFont.Weight.Bold))
        title_frame.addWidget(title)
        subtitle = QLabel("实时修音 / 人声增强 / 直播路由")
        subtitle.setProperty("muted", True)
        subtitle.setFont(QFont("Microsoft YaHei UI", 10))
        title_frame.addWidget(subtitle)
        header.addLayout(title_frame)

        header.addStretch()

        self._status_label = QLabel(f"就绪 · {self._engine_available()}")
        self._status_label.setStyleSheet(f"background: {C_ACCENT}; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold;")
        header.addWidget(self._status_label)
        main_layout.addLayout(header)

        # tabs
        self._tabs = QTabWidget()
        main_layout.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_live_tab(), "一键直播")
        self._tabs.addTab(self._build_settings_tab(), "高级设置")
        self._tabs.addTab(self._build_test_tab(), "效果测试")
        self._tabs.addTab(self._build_route_tab(), "虚拟声卡")

    # -------------------------------------------------------------------
    # Live tab
    # -------------------------------------------------------------------

    def _build_live_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(16)

        # left: controls
        left = QVBoxLayout()
        left.setSpacing(12)

        # device group
        dev_group = QGroupBox("设备选择")
        dev_layout = QVBoxLayout(dev_group)

        row = QHBoxLayout()
        row.addWidget(QLabel("输入"))
        self._input_combo = QComboBox()
        self._input_combo.setMinimumWidth(280)
        row.addWidget(self._input_combo, 1)
        dev_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("输出"))
        self._output_combo = QComboBox()
        self._output_combo.setMinimumWidth(280)
        row.addWidget(self._output_combo, 1)
        dev_layout.addLayout(row)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._load_devices)
        dev_layout.addWidget(refresh_btn)
        left.addWidget(dev_group)

        # auto mode group
        auto_group = QGroupBox("自动模式")
        auto_layout = QVBoxLayout(auto_group)

        self._auto_check = QCheckBox("自动识别调号并自动调参")
        self._auto_check.setChecked(True)
        auto_layout.addWidget(self._auto_check)

        self._auto_status = QLabel("自动识别已开启，点击一键开始即可")
        self._auto_status.setStyleSheet(f"color: {C_ACCENT}; font-size: 14px;")
        auto_layout.addWidget(self._auto_status)

        btn_row = QHBoxLayout()
        start_btn = QPushButton("一键开始直播修音")
        start_btn.setProperty("accent", True)
        start_btn.clicked.connect(self._one_click_start)
        btn_row.addWidget(start_btn)
        stop_btn = QPushButton("停止")
        stop_btn.clicked.connect(self._stop_audio)
        btn_row.addWidget(stop_btn)
        auto_layout.addLayout(btn_row)
        left.addWidget(auto_group)

        # feedback group
        fb_group = QGroupBox("实时反馈")
        fb_layout = QVBoxLayout(fb_group)

        self._pitch_label = QLabel("-- Hz")
        self._target_label = QLabel("--")
        self._shift_label = QLabel("0.00 st")
        for name, var in [("检测音高", self._pitch_label), ("目标音", self._target_label), ("修正量", self._shift_label)]:
            row = QHBoxLayout()
            lbl = QLabel(name)
            lbl.setProperty("muted", True)
            row.addWidget(lbl)
            row.addStretch()
            var.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            row.addWidget(var)
            fb_layout.addLayout(row)
        left.addWidget(fb_group)

        # spectrum
        spec_group = QGroupBox("频谱")
        spec_layout = QVBoxLayout(spec_group)
        self._spectrum = SpectrumDisplay()
        spec_layout.addWidget(self._spectrum)
        left.addWidget(spec_group)

        layout.addLayout(left, 1)

        # right: gauges
        right = QVBoxLayout()
        right.setSpacing(12)

        gauge_group = QGroupBox("音高偏差")
        gauge_layout = QVBoxLayout(gauge_group)
        self._pitch_gauge = PitchGauge()
        gauge_layout.addWidget(self._pitch_gauge)
        right.addWidget(gauge_group)

        level_group = QGroupBox("输出音量")
        level_layout = QVBoxLayout(level_group)
        self._level_meter = LevelMeter()
        level_layout.addWidget(self._level_meter)
        right.addWidget(level_group)

        layout.addLayout(right)

        return tab

    # -------------------------------------------------------------------
    # Settings tab
    # -------------------------------------------------------------------

    def _build_settings_tab(self) -> QWidget:
        from ..dsp import NOTE_NAMES

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # preset bar
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("预设"))
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(list(self.presets.keys()))
        self._preset_combo.setCurrentText(self._cfg.get("preset", "流行"))
        preset_row.addWidget(self._preset_combo)
        apply_btn = QPushButton("应用")
        apply_btn.setProperty("accent", True)
        apply_btn.clicked.connect(self._apply_preset)
        preset_row.addWidget(apply_btn)
        save_btn = QPushButton("保存为新预设")
        save_btn.clicked.connect(self._save_preset)
        preset_row.addWidget(save_btn)
        del_btn = QPushButton("删除预设")
        del_btn.clicked.connect(self._delete_preset)
        preset_row.addWidget(del_btn)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        # two columns
        columns = QHBoxLayout()
        columns.setSpacing(16)

        # left: tuning
        tune_group = QGroupBox("修音")
        tune_layout = QVBoxLayout(tune_group)

        row = QHBoxLayout()
        row.addWidget(QLabel("调号"))
        self._root_combo = QComboBox()
        self._root_combo.addItems(NOTE_NAMES)
        self._root_combo.setCurrentText(self._cfg.get("root", "C"))
        row.addWidget(self._root_combo)
        row.addWidget(QLabel("调式"))
        self._scale_combo = QComboBox()
        self._scale_combo.addItems(["大调", "小调", "半音阶"])
        self._scale_combo.setCurrentText(self._cfg.get("scale", "大调"))
        row.addWidget(self._scale_combo)
        detect_btn = QPushButton("智能识别")
        detect_btn.clicked.connect(self._detect_key)
        row.addWidget(detect_btn)
        tune_layout.addLayout(row)

        self._sl_amount = ParamSlider("修音强度", 0.0, 1.0)
        self._sl_amount.set_value(self._cfg.get("amount", 0.7))
        tune_layout.addWidget(self._sl_amount)

        self._sl_speed = ParamSlider("修音速度", 0.01, 1.0)
        self._sl_speed.set_value(self._cfg.get("speed", 0.25))
        tune_layout.addWidget(self._sl_speed)

        self._sl_mix = ParamSlider("干湿比", 0.0, 1.0)
        self._sl_mix.set_value(self._cfg.get("mix", 0.8))
        tune_layout.addWidget(self._sl_mix)

        self._auto_override = QCheckBox("自动模式覆盖参数")
        self._auto_override.setChecked(self._cfg.get("auto_mode", True))
        tune_layout.addWidget(self._auto_override)
        tune_layout.addStretch()
        columns.addWidget(tune_group)

        # right: output + voice
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        out_group = QGroupBox("监听与输出")
        out_layout = QVBoxLayout(out_group)
        self._sl_gain = ParamSlider("增益", 0.2, 2.0)
        self._sl_gain.set_value(self._cfg.get("gain", 1.0))
        out_layout.addWidget(self._sl_gain)
        self._bypass_check = QCheckBox("旁路修音")
        self._bypass_check.setChecked(self._cfg.get("bypass", False))
        out_layout.addWidget(self._bypass_check)
        out_layout.addStretch()
        right_col.addWidget(out_group)

        voice_group = QGroupBox("人声处理")
        voice_layout = QVBoxLayout(voice_group)
        self._sl_gate = ParamSlider("噪声门", 0.0, 1.0)
        self._sl_gate.set_value(self._cfg.get("gate", 0.25))
        voice_layout.addWidget(self._sl_gate)
        self._sl_comp = ParamSlider("压缩", 0.0, 1.0)
        self._sl_comp.set_value(self._cfg.get("compression", 0.4))
        voice_layout.addWidget(self._sl_comp)
        self._sl_bright = ParamSlider("亮度", 0.0, 1.0)
        self._sl_bright.set_value(self._cfg.get("brightness", 0.25))
        voice_layout.addWidget(self._sl_bright)
        self._sl_deess = ParamSlider("齿音消除", 0.0, 1.0)
        self._sl_deess.set_value(self._cfg.get("deesser", 0.3))
        voice_layout.addWidget(self._sl_deess)
        self._sl_reverb = ParamSlider("混响", 0.0, 1.0)
        self._sl_reverb.set_value(self._cfg.get("reverb", 0.15))
        voice_layout.addWidget(self._sl_reverb)
        right_col.addWidget(voice_group)

        columns.addLayout(right_col, 1)
        layout.addLayout(columns, 1)

        # bottom buttons
        btn_row = QHBoxLayout()
        start_btn = QPushButton("开始直播处理")
        start_btn.setProperty("accent", True)
        start_btn.clicked.connect(self._start_audio)
        btn_row.addWidget(start_btn)
        stop_btn = QPushButton("停止")
        stop_btn.clicked.connect(self._stop_audio)
        btn_row.addWidget(stop_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return tab

    # -------------------------------------------------------------------
    # Test tab
    # -------------------------------------------------------------------

    def _build_test_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        group = QGroupBox("录音对比测试")
        g_layout = QVBoxLayout(group)

        desc = QLabel("录 5 秒人声，软件会用当前参数生成处理后版本。对比原声和修音效果，再决定是否用于直播。")
        desc.setProperty("muted", True)
        desc.setWordWrap(True)
        g_layout.addWidget(desc)

        self._test_status = QLabel("尚未录制测试音频")
        self._test_status.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        g_layout.addWidget(self._test_status)

        btn_row = QHBoxLayout()
        rec_btn = QPushButton("录制 5 秒")
        rec_btn.setProperty("accent", True)
        rec_btn.clicked.connect(self._record_test)
        btn_row.addWidget(rec_btn)
        orig_btn = QPushButton("播放原声")
        orig_btn.clicked.connect(lambda: self._play_test("original"))
        btn_row.addWidget(orig_btn)
        proc_btn = QPushButton("播放处理后")
        proc_btn.clicked.connect(lambda: self._play_test("processed"))
        btn_row.addWidget(proc_btn)
        ab_btn = QPushButton("A/B 连续对比")
        ab_btn.clicked.connect(self._play_ab)
        btn_row.addWidget(ab_btn)
        btn_row.addStretch()
        g_layout.addLayout(btn_row)

        layout.addWidget(group)
        layout.addStretch()
        return tab

    # -------------------------------------------------------------------
    # Route tab
    # -------------------------------------------------------------------

    def _build_route_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        group = QGroupBox("虚拟声卡模式")
        g_layout = QVBoxLayout(group)

        desc = QLabel("选择 CABLE Input / Voicemeeter Input 后，直播软件选择对应 Output，获得类似虚拟麦克风的路由效果。")
        desc.setProperty("muted", True)
        desc.setWordWrap(True)
        g_layout.addWidget(desc)

        self._route_status = QLabel("选择虚拟声卡输出后，可发送测试音")
        self._route_status.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        g_layout.addWidget(self._route_status)

        btn_row = QHBoxLayout()
        find_btn = QPushButton("自动查找虚拟声卡")
        find_btn.setProperty("accent", True)
        find_btn.clicked.connect(self._find_virtual)
        btn_row.addWidget(find_btn)
        test_btn = QPushButton("发送 1 秒测试音")
        test_btn.clicked.connect(self._send_test_tone)
        btn_row.addWidget(test_btn)
        refresh_btn = QPushButton("刷新设备")
        refresh_btn.clicked.connect(self._load_devices)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        g_layout.addLayout(btn_row)

        layout.addWidget(group)

        steps_group = QGroupBox("直播软件设置")
        s_layout = QVBoxLayout(steps_group)
        steps = QLabel(
            '1. 本软件"输出"选择 CABLE Input\n'
            '2. OBS/直播伴侣"麦克风"选择 CABLE Output\n'
            '3. 点击"发送 1 秒测试音"，在直播软件音量条看到跳动即可\n'
            '4. 回到"一键直播"，点击"一键开始直播修音"'
        )
        steps.setProperty("dim", True)
        s_layout.addWidget(steps)
        layout.addWidget(steps_group)

        layout.addStretch()
        return tab

    # -------------------------------------------------------------------
    # Backend integration
    # -------------------------------------------------------------------

    def _get_config(self) -> dict[str, object]:
        return {
            "root": self._root_combo.currentText() if hasattr(self, '_root_combo') else self._cfg.get("root", "C"),
            "scale": self._scale_combo.currentText() if hasattr(self, '_scale_combo') else self._cfg.get("scale", "大调"),
            "amount": self._sl_amount.value() if hasattr(self, '_sl_amount') else self._cfg.get("amount", 0.7),
            "speed": self._sl_speed.value() if hasattr(self, '_sl_speed') else self._cfg.get("speed", 0.25),
            "mix": self._sl_mix.value() if hasattr(self, '_sl_mix') else self._cfg.get("mix", 0.8),
            "gate": self._sl_gate.value() if hasattr(self, '_sl_gate') else self._cfg.get("gate", 0.25),
            "compression": self._sl_comp.value() if hasattr(self, '_sl_comp') else self._cfg.get("compression", 0.4),
            "brightness": self._sl_bright.value() if hasattr(self, '_sl_bright') else self._cfg.get("brightness", 0.25),
            "gain": self._sl_gain.value() if hasattr(self, '_sl_gain') else self._cfg.get("gain", 1.0),
            "bypass": self._bypass_check.isChecked() if hasattr(self, '_bypass_check') else self._cfg.get("bypass", False),
            "auto_mode": self._auto_check.isChecked() if hasattr(self, '_auto_check') else self._cfg.get("auto_mode", True),
            "deesser": self._sl_deess.value() if hasattr(self, '_sl_deess') else self._cfg.get("deesser", 0.3),
            "reverb": self._sl_reverb.value() if hasattr(self, '_sl_reverb') else self._cfg.get("reverb", 0.15),
            "preset": self._preset_combo.currentText() if hasattr(self, '_preset_combo') else self._cfg.get("preset", "流行"),
            "input_device": self._input_combo.currentText() if hasattr(self, '_input_combo') else "默认输入",
            "output_device": self._output_combo.currentText() if hasattr(self, '_output_combo') else "默认输出",
        }

    def _selected_device(self, values: list[tuple[str, int | None]], selected: str) -> int | None:
        for name, index in values:
            if name == selected:
                return index
        return None

    def _load_devices(self) -> None:
        if sd is None:
            self._status_label.setText("缺少音频依赖")
            return
        devices = sd.query_devices()
        self.input_devices = [("默认输入", None)]
        self.output_devices = [("默认输出", None)]
        for idx, dev in enumerate(devices):
            name = f"{idx}: {dev['name']}"
            if int(dev["max_input_channels"]) > 0:
                self.input_devices.append((name, idx))
            if int(dev["max_output_channels"]) > 0:
                self.output_devices.append((name, idx))

        self._input_combo.clear()
        self._input_combo.addItems([n for n, _ in self.input_devices])
        self._output_combo.clear()
        self._output_combo.addItems([n for n, _ in self.output_devices])

    def _apply_preset(self) -> None:
        name = self._preset_combo.currentText()
        preset = self.presets.get(name)
        if not preset:
            return
        self._sl_amount.set_value(preset.get("amount", 0.7))
        self._sl_speed.set_value(preset.get("speed", 0.25))
        self._sl_mix.set_value(preset.get("mix", 0.8))
        self._sl_gate.set_value(preset.get("gate", 0.25))
        self._sl_comp.set_value(preset.get("compression", 0.4))
        self._sl_bright.set_value(preset.get("brightness", 0.25))
        self._sl_gain.set_value(preset.get("gain", 1.0))
        self._sl_deess.set_value(preset.get("deesser", 0.3))
        self._sl_reverb.set_value(preset.get("reverb", 0.15))

    def _save_preset(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        from ..settings import BUILT_IN_PRESETS, merged_presets, preset_from_config, save_state
        name, ok = QInputDialog.getText(self, "保存预设", "预设名称")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in BUILT_IN_PRESETS:
            return
        self.user_presets[name] = preset_from_config(self._get_config())
        self.presets = merged_presets(self.user_presets)
        self._preset_combo.clear()
        self._preset_combo.addItems(list(self.presets.keys()))
        self._preset_combo.setCurrentText(name)
        save_state(self._get_config(), self.user_presets)

    def _delete_preset(self) -> None:
        from ..settings import BUILT_IN_PRESETS, merged_presets, save_state
        name = self._preset_combo.currentText()
        if name in BUILT_IN_PRESETS or name not in self.user_presets:
            return
        del self.user_presets[name]
        self.presets = merged_presets(self.user_presets)
        self._preset_combo.clear()
        self._preset_combo.addItems(list(self.presets.keys()))
        self._preset_combo.setCurrentText("流行")
        save_state(self._get_config(), self.user_presets)

    def _detect_key(self) -> None:
        if sd is None:
            return
        input_dev = self._selected_device(self.input_devices, self._input_combo.currentText())
        self._status_label.setText("正在录制调号识别")
        threading.Thread(target=self._detect_key_worker, args=(input_dev,), daemon=True).start()

    def _detect_key_worker(self, input_dev: int | None) -> None:
        from ..dsp import estimate_key_from_audio
        try:
            rec = sd.rec(SAMPLE_RATE * 5, samplerate=SAMPLE_RATE, channels=1, dtype="float32", device=input_dev)
            sd.wait()
            samples = rec[:, 0].astype(np.float32, copy=True)
            result = estimate_key_from_audio(samples, SAMPLE_RATE)
            if result:
                root, scale, conf = result
                self._cfg["root"] = root
                self._cfg["scale"] = SCALE_TO_LABEL.get(scale, "半音阶")
                self._root_combo.setCurrentText(root)
                self._scale_combo.setCurrentText(SCALE_TO_LABEL.get(scale, "半音阶"))
                self._status_label.setText(f"已识别：{root} {SCALE_TO_LABEL.get(scale, '半音阶')} · 置信度 {conf:.0%}")
            else:
                self._status_label.setText("未识别到稳定音高")
        except Exception as exc:
            self.logger.exception("Key detection failed")
            self._status_label.setText(f"识别失败: {exc}")

    def _one_click_start(self) -> None:
        self._auto_check.setChecked(True)
        self._bypass_check.setChecked(False)
        self._auto_status.setText("自动识别中：请正常唱歌，软件会边听边调整")
        self._start_audio()

    def _start_audio(self) -> None:
        if sd is None:
            return
        if self.audio_thread and self.audio_thread.is_alive():
            return
        self.stop_event.clear()
        self.engine.reset()
        self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.audio_thread.start()
        self._status_label.setText("正在启动")

    def _stop_audio(self) -> None:
        self.stop_event.set()
        if self.stream:
            self.stream.abort()
            self.stream.close()
            self.stream = None
        self._status_label.setText("已停止")

    def _audio_worker(self) -> None:
        config = self._get_config()
        input_dev = self._selected_device(self.input_devices, config.get("input_device", ""))
        output_dev = self._selected_device(self.output_devices, config.get("output_device", ""))

        def callback(indata: np.ndarray, outdata: np.ndarray, frames: int, time_info: object, status: object) -> None:
            mono = indata[:, 0].astype(np.float32, copy=True)
            cfg = self._get_config()
            cfg["scale"] = SCALE_LABELS.get(str(cfg["scale"]), str(cfg["scale"]))
            result = self.engine.process_block(mono, cfg)
            outdata[:] = result.audio.reshape(-1, 1)
            level = float(np.sqrt(np.mean(result.audio ** 2)))

            if result.audio.size >= 256:
                spec = np.abs(np.fft.rfft(result.audio * np.hanning(result.audio.size)))
                freqs = np.fft.rfftfreq(result.audio.size, 1.0 / SAMPLE_RATE)
                mask = (freqs >= 80) & (freqs <= 8000)
                vocal_spec = spec[mask] if np.any(mask) else spec[:32]
            else:
                vocal_spec = np.zeros(32, dtype=np.float32)

            cents = 0.0
            if result.note and result.frequency:
                from ..dsp import frequency_to_midi
                cents = (frequency_to_midi(result.frequency) - result.note.midi) * 100.0

            self._push_status({
                "frequency": result.frequency,
                "target": result.note.name if result.note else "--",
                "semitones": result.semitones,
                "level": min(1.0, level * 3.0),
                "status": f"运行中 · {result.engine}",
                "auto_status": result.auto_status,
                "cents": cents,
                "spectrum": vocal_spec.astype(np.float32),
            })

        try:
            self.stream = sd.Stream(
                samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, dtype="float32",
                channels=1, device=(input_dev, output_dev), callback=callback, latency="low",
            )
            with self.stream:
                while not self.stop_event.wait(0.1):
                    pass
        except Exception as exc:
            self.logger.exception("Audio worker failed")
            self._push_status({"error": str(exc)})

    def _record_test(self) -> None:
        if sd is None:
            return
        if self.audio_thread and self.audio_thread.is_alive():
            self._stop_audio()
        input_dev = self._selected_device(self.input_devices, self._input_combo.currentText())
        self._test_status.setText("正在录制 5 秒...")
        threading.Thread(target=self._record_test_worker, args=(input_dev,), daemon=True).start()

    def _record_test_worker(self, input_dev: int | None) -> None:
        from ..audio_engine import process_offline_audio
        try:
            rec = sd.rec(SAMPLE_RATE * 5, samplerate=SAMPLE_RATE, channels=1, dtype="float32", device=input_dev)
            sd.wait()
            original = rec[:, 0].astype(np.float32, copy=True)
            cfg = self._get_config()
            cfg["scale"] = SCALE_LABELS.get(str(cfg["scale"]), str(cfg["scale"]))
            processed = process_offline_audio(original, cfg, SAMPLE_RATE, BLOCK_SIZE, PITCH_WINDOW)
            self._test_original = original
            self._test_processed = processed
            self._test_status.setText("测试音频已生成，可以播放对比")
        except Exception as exc:
            self.logger.exception("Effect test failed")
            self._test_status.setText(f"测试失败: {exc}")

    def _play_test(self, kind: str) -> None:
        data = getattr(self, '_test_original' if kind == "original" else '_test_processed', None)
        if data is None:
            self._test_status.setText("请先录制")
            return
        output_dev = self._selected_device(self.output_devices, self._output_combo.currentText())
        self._test_status.setText(f"正在播放{'原声' if kind == 'original' else '处理后'}...")
        threading.Thread(target=self._play_worker, args=(data, output_dev), daemon=True).start()

    def _play_ab(self) -> None:
        orig = getattr(self, '_test_original', None)
        proc = getattr(self, '_test_processed', None)
        if orig is None or proc is None:
            self._test_status.setText("请先录制")
            return
        silence = np.zeros(int(SAMPLE_RATE * 0.4), dtype=np.float32)
        combined = np.concatenate([orig, silence, proc]).astype(np.float32)
        output_dev = self._selected_device(self.output_devices, self._output_combo.currentText())
        self._test_status.setText("正在播放 A/B 对比...")
        threading.Thread(target=self._play_worker, args=(combined, output_dev), daemon=True).start()

    def _play_worker(self, data: np.ndarray, output_dev: int | None) -> None:
        try:
            sd.play(data.reshape(-1, 1), samplerate=SAMPLE_RATE, device=output_dev)
            sd.wait()
            self._test_status.setText("播放完成")
        except Exception as exc:
            self._test_status.setText(f"播放失败: {exc}")

    def _find_virtual(self) -> None:
        keywords = ("cable input", "vb-audio", "voicemeeter input", "virtual", "blackhole")
        for name, _ in self.output_devices:
            if any(kw in name.lower() for kw in keywords):
                self._output_combo.setCurrentText(name)
                self._route_status.setText(f"已选择：{name}")
                return
        self._route_status.setText("未找到虚拟声卡，请先安装 VB-CABLE 或 Voicemeeter")

    def _send_test_tone(self) -> None:
        t = np.arange(int(SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE
        tone = (0.18 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
        output_dev = self._selected_device(self.output_devices, self._output_combo.currentText())
        self._route_status.setText("正在向当前输出发送测试音")
        threading.Thread(target=self._play_worker, args=(tone, output_dev), daemon=True).start()

    # -------------------------------------------------------------------
    # Status & animation
    # -------------------------------------------------------------------

    def _push_status(self, status: dict[str, object]) -> None:
        try:
            self.status_queue.put_nowait(status)
        except queue.Full:
            try:
                self.status_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.status_queue.put_nowait(status)
            except queue.Full:
                pass

    def _poll_status(self) -> None:
        try:
            while True:
                status = self.status_queue.get_nowait()
                if "error" in status:
                    self._status_label.setText("音频错误")
                    continue
                freq = status.get("frequency")
                self._pitch_label.setText(f"{freq:.1f} Hz" if isinstance(freq, float) else "--")
                self._target_label.setText(str(status.get("target", "--")))
                self._shift_label.setText(f"{float(status.get('semitones', 0.0)):.2f} st")
                self._status_label.setText(str(status.get("status", "运行中")))
                auto = status.get("auto_status")
                if isinstance(auto, str) and auto:
                    self._auto_status.setText(auto)
                self._level = float(status.get("level", 0.0))
                self._cents = float(status.get("cents", 0.0))
                self._note = str(status.get("target", "--"))
                self._freq = float(status.get("frequency", 0.0) or 0.0)
                spec = status.get("spectrum")
                if isinstance(spec, np.ndarray):
                    self._spec = spec
        except queue.Empty:
            pass

    def _animate(self) -> None:
        self._level_meter.set_level(getattr(self, '_level', 0.0))
        self._level_meter.tick()
        self._pitch_gauge.set_values(
            getattr(self, '_cents', 0.0),
            getattr(self, '_note', '--'),
            getattr(self, '_freq', 0.0),
        )
        self._pitch_gauge.tick()
        self._spectrum.set_spectrum(getattr(self, '_spec', np.zeros(32, dtype=np.float32)))
        self._spectrum.tick()

    def closeEvent(self, event: object) -> None:
        from ..settings import save_state
        self._stop_audio()
        try:
            save_state(self._get_config(), self.user_presets)
        except OSError:
            pass
        self.logger.info("Application closed")
        super().closeEvent(event)
