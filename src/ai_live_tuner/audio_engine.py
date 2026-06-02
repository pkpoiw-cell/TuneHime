from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .dsp import (
    Note,
    ParamSmoother,
    PitchSmoother,
    detect_pitch_yin,
    estimate_key_from_audio,
    nearest_allowed_note,
    soft_limiter,
)

from pedalboard import (
    Compressor,
    HighShelfFilter,
    HighpassFilter,
    Limiter,
    NoiseGate,
    Pedalboard,
    PitchShift,
    Reverb,
)


@dataclass
class ProcessResult:
    audio: np.ndarray
    frequency: float | None
    note: Note | None
    semitones: float
    engine: str
    auto_status: str = ""


@dataclass
class AutoAdjustResult:
    config: dict[str, object]
    status: str


class RealtimeVoiceEngine:
    def __init__(self, sample_rate: int, block_size: int, pitch_window: int) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.pitch_window = pitch_window

        self.pitch_smoother = PitchSmoother(history_size=9, smoothing=0.35)

        # parameter smoothers to avoid zipper noise
        self._sm_amount = ParamSmoother(0.7, 0.12)
        self._sm_speed = ParamSmoother(0.25, 0.12)
        self._sm_mix = ParamSmoother(0.8, 0.15)
        self._sm_gate = ParamSmoother(0.25, 0.10)
        self._sm_compression = ParamSmoother(0.4, 0.10)
        self._sm_brightness = ParamSmoother(0.25, 0.10)
        self._sm_gain = ParamSmoother(1.0, 0.12)
        self._sm_deesser = ParamSmoother(0.3, 0.10)
        self._sm_reverb = ParamSmoother(0.15, 0.10)

        self._init_engine()
        self.auto_adjust = AutoAdjustState(sample_rate, pitch_window)

    def _init_engine(self) -> None:
        """Initialize pedalboard plugins and pitch state."""
        self.pitch_buffer = np.zeros(self.pitch_window, dtype=np.float32)
        self.current_semitones = 0.0
        self.pitch_smoother.reset() if hasattr(self, 'pitch_smoother') else None

        self.pitch_shift = PitchShift(semitones=0.0)
        self.highpass = HighpassFilter(cutoff_frequency_hz=75.0)
        self.gate = NoiseGate(threshold_db=-45.0, ratio=3.0, attack_ms=3.0, release_ms=90.0)
        self.compressor = Compressor(threshold_db=-18.0, ratio=3.0, attack_ms=4.0, release_ms=90.0)
        self.brightness = HighShelfFilter(cutoff_frequency_hz=4200.0, gain_db=2.0, q=0.707)
        self.limiter = Limiter(threshold_db=-1.0, release_ms=60.0)
        self.pedalboard_reverb = Reverb(room_size=0.5, damping=0.5, wet_level=0.15, dry_level=0.85)

        # reusable pedalboard chain (highpass -> gate -> compressor -> brightness -> limiter)
        self._board = Pedalboard([
            self.highpass, self.gate, self.compressor, self.brightness, self.limiter,
        ])

    def reset(self) -> None:
        self._init_engine()
        self.auto_adjust = AutoAdjustState(self.sample_rate, self.pitch_window)

    def _smooth_config(self, config: dict[str, object]) -> dict[str, object]:
        return {
            "root": config["root"],
            "scale": config["scale"],
            "amount": self._sm_amount.process(float(config["amount"])),
            "speed": self._sm_speed.process(float(config["speed"])),
            "mix": self._sm_mix.process(float(config["mix"])),
            "gate": self._sm_gate.process(float(config["gate"])),
            "compression": self._sm_compression.process(float(config["compression"])),
            "brightness": self._sm_brightness.process(float(config["brightness"])),
            "gain": self._sm_gain.process(float(config["gain"])),
            "bypass": config["bypass"],
            "deesser": self._sm_deesser.process(float(config.get("deesser", 0.3))),
            "reverb": self._sm_reverb.process(float(config.get("reverb", 0.15))),
        }

    def process_block(self, block: np.ndarray, config: dict[str, object]) -> ProcessResult:
        mono = np.asarray(block, dtype=np.float32)
        auto_status = ""
        if bool(config.get("auto_mode", False)):
            adjusted = self.auto_adjust.process(mono, config)
            config = adjusted.config
            auto_status = adjusted.status

        config = self._smooth_config(config)

        frames = mono.size
        if frames > self.pitch_buffer.size:
            self.pitch_buffer = np.zeros(frames, dtype=np.float32)
        self.pitch_buffer = np.roll(self.pitch_buffer, -frames)
        self.pitch_buffer[-frames:] = mono

        frequency = detect_pitch_yin(self.pitch_buffer, self.sample_rate)
        frequency = self.pitch_smoother.process(frequency)

        note, semitones = self._target_shift(frequency, config)

        if bool(config["bypass"]):
            processed = mono.copy()
            semitones = 0.0
        else:
            processed = self._process_with_pedalboard(mono, semitones, config)

        return ProcessResult(processed.astype(np.float32), frequency, note, semitones, "专业引擎", auto_status)

    def _target_shift(self, frequency: float | None, config: dict[str, object]) -> tuple[Note | None, float]:
        if frequency is None:
            target = 0.0
            note = None
        else:
            note = nearest_allowed_note(frequency, str(config["root"]), str(config["scale"]))
            target = 12.0 * np.log2(note.frequency / frequency) * float(config["amount"])

        smoothing = float(np.clip(config["speed"], 0.01, 1.0))
        self.current_semitones += (target - self.current_semitones) * smoothing
        return note, float(self.current_semitones)

    def _process_with_pedalboard(self, mono: np.ndarray, semitones: float, config: dict[str, object]) -> np.ndarray:
        # update plugin parameters from config
        self.pitch_shift.semitones = float(np.clip(semitones, -12.0, 12.0))
        self.gate.threshold_db = -60.0 + float(config["gate"]) * 35.0
        self.compressor.threshold_db = -10.0 - float(config["compression"]) * 18.0
        self.compressor.ratio = 1.2 + float(config["compression"]) * 5.0
        self.brightness.gain_db = float(config["brightness"]) * 6.0

        # pitch shift
        corrected = self.pitch_shift(mono, self.sample_rate)

        # equal-power crossfade for dry/wet mix
        wet = float(np.clip(config["mix"], 0.0, 1.0))
        dry_gain = np.cos(wet * np.pi * 0.5)
        wet_gain = np.sin(wet * np.pi * 0.5)
        blended = (mono * dry_gain + corrected * wet_gain).astype(np.float32)

        # process through pedalboard chain
        processed = self._board(blended, self.sample_rate)

        # reverb
        reverb_amount = float(config.get("reverb", 0.15))
        if reverb_amount > 0.001:
            self.pedalboard_reverb.wet_level = reverb_amount * 0.35
            self.pedalboard_reverb.dry_level = 1.0 - reverb_amount * 0.35
            processed = self.pedalboard_reverb(processed, self.sample_rate)

        # output gain + safety limiter
        return soft_limiter(processed * float(config["gain"]), drive=1.2)


def process_offline_audio(
    samples: np.ndarray,
    config: dict[str, object],
    sample_rate: int,
    block_size: int,
    pitch_window: int,
) -> np.ndarray:
    engine = RealtimeVoiceEngine(sample_rate, block_size, pitch_window)
    chunks: list[np.ndarray] = []
    for start in range(0, samples.size, block_size):
        chunks.append(engine.process_block(samples[start : start + block_size], config).audio)
    return np.concatenate(chunks).astype(np.float32)


def engine_available() -> str:
    return "专业引擎"


class AutoAdjustState:
    def __init__(self, sample_rate: int, pitch_window: int) -> None:
        self.sample_rate = sample_rate
        self.buffer_size = sample_rate * 5
        self.analysis_buffer = np.zeros(self.buffer_size, dtype=np.float32)
        self._write_pos = 0
        self.blocks_seen = 0
        self.root = "C"
        self.scale = "major"
        self.confidence = 0.0
        self.noise_floor = 0.01
        self.pitch_window = pitch_window

    def _append_to_buffer(self, x: np.ndarray) -> None:
        """Ring buffer write — O(block_size) instead of O(buffer_size)."""
        n = x.size
        pos = self._write_pos
        end = pos + n
        if end <= self.buffer_size:
            self.analysis_buffer[pos:end] = x
        else:
            first = self.buffer_size - pos
            self.analysis_buffer[pos:] = x[:first]
            self.analysis_buffer[:n - first] = x[first:]
        self._write_pos = end % self.buffer_size

    def process(self, block: np.ndarray, config: dict[str, object]) -> AutoAdjustResult:
        x = np.asarray(block, dtype=np.float32)
        self.blocks_seen += 1
        self._append_to_buffer(x)

        rms = float(np.sqrt(np.mean(x * x))) if x.size else 0.0
        peak = float(np.max(np.abs(x))) if x.size else 0.0
        if rms < max(0.025, self.noise_floor * 2.8):
            self.noise_floor = self.noise_floor * 0.98 + max(rms, 0.001) * 0.02

        if self.blocks_seen % 18 == 0:
            key = estimate_key_from_audio(self.analysis_buffer, self.sample_rate)
            if key is not None:
                self.root, self.scale, self.confidence = key

        adjusted = dict(config)
        adjusted["root"] = self.root
        adjusted["scale"] = self.scale
        adjusted["amount"] = 0.68 + min(0.22, self.confidence * 0.18)
        adjusted["speed"] = 0.24 + min(0.28, self.confidence * 0.22)
        adjusted["mix"] = 0.82
        adjusted["gate"] = float(np.clip(self.noise_floor * 20.0 + 0.18, 0.18, 0.62))

        crest = peak / max(rms, 1e-5)
        adjusted["compression"] = float(np.clip((crest - 2.2) / 7.0 + 0.35, 0.28, 0.78))

        high_ratio = self._high_frequency_ratio(x)
        if high_ratio < 0.12:
            brightness = 0.58
        elif high_ratio > 0.35:
            brightness = 0.26
        else:
            brightness = 0.42
        adjusted["brightness"] = brightness
        adjusted["gain"] = float(np.clip(0.95 / max(rms * 6.0, 0.55), 0.82, 1.18))
        adjusted["deesser"] = float(np.clip(0.25 + high_ratio * 0.6, 0.15, 0.55))
        adjusted["reverb"] = float(np.clip(0.12 + (0.6 - crest) * 0.08, 0.05, 0.25))

        status = f"自动：{self.root} {'大调' if self.scale == 'major' else '小调'} · 噪声门 {adjusted['gate']:.2f}"
        return AutoAdjustResult(adjusted, status)

    def _high_frequency_ratio(self, block: np.ndarray) -> float:
        if block.size < 128:
            return 0.0
        spectrum = np.abs(np.fft.rfft(block * np.hanning(block.size)))
        if spectrum.size < 4:
            return 0.0
        freqs = np.fft.rfftfreq(block.size, 1.0 / self.sample_rate)
        total = float(np.sum(spectrum) + 1e-9)
        high = float(np.sum(spectrum[freqs >= 4000.0]))
        return high / total
