from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import log2

import numpy as np


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
SCALES = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "chromatic": tuple(range(12)),
}


@dataclass(frozen=True)
class Note:
    name: str
    midi: int
    frequency: float


def midi_to_frequency(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def frequency_to_midi(frequency: float) -> float:
    return 69.0 + 12.0 * log2(frequency / 440.0)


def midi_note_name(midi_note: int) -> str:
    octave = midi_note // 12 - 1
    return f"{NOTE_NAMES[midi_note % 12]}{octave}"


# ---------------------------------------------------------------------------
# Pitch detection: YIN (CMNDF) algorithm — FFT-optimized
# ---------------------------------------------------------------------------

def detect_pitch_yin(
    samples: np.ndarray,
    sample_rate: int,
    min_freq: float = 70.0,
    max_freq: float = 900.0,
    threshold: float = 0.20,
) -> float | None:
    """Detect monophonic pitch using the YIN CMNDF algorithm.

    Uses FFT-based autocorrelation for the difference function (O(N log N))
    and np.cumsum for the CMNDF. Returns frequency in Hz or None if unreliable.
    """
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim != 1:
        return None

    # remove DC offset
    x = x - float(np.mean(x))

    n = x.size
    min_lag = max(2, int(sample_rate / max_freq))
    max_lag = min(n - 2, int(sample_rate / min_freq))
    if max_lag <= min_lag or n < max_lag + 1:
        return None

    # apply Hanning window to reduce spectral leakage
    windowed = x * np.hanning(n).astype(np.float32)

    # Step 1: difference function via FFT-based autocorrelation
    # YIN difference: d(tau) = sum((x[j] - x[j+tau])^2)
    #               = sum(x[j]^2) + sum(x[j+tau]^2) - 2*corr(tau)
    fft_size = 1
    while fft_size < 2 * n:
        fft_size <<= 1
    X = np.fft.rfft(windowed, n=fft_size)
    corr_full = np.fft.irfft(X * np.conj(X))[:max_lag + 1].real

    # energy terms
    cumsum_sq = np.empty(n + 1, dtype=np.float64)
    cumsum_sq[0] = 0.0
    cumsum_sq[1:] = np.cumsum(windowed.astype(np.float64) ** 2)

    diff = np.empty(max_lag, dtype=np.float64)
    for tau in range(max_lag):
        diff[tau] = cumsum_sq[n - tau] + cumsum_sq[n] - cumsum_sq[tau] - 2.0 * corr_full[tau]
    diff = np.maximum(diff, 0.0).astype(np.float32)
    diff[0] = 0.0

    # Step 2: cumulative mean normalized difference function (CMNDF)
    cumsum_diff = np.cumsum(diff)
    cmndf = np.ones(max_lag, dtype=np.float32)
    for tau in range(1, max_lag):
        mean = cumsum_diff[tau] / tau
        if mean > 1e-12:
            cmndf[tau] = diff[tau] / mean

    # Step 3: find first dip below threshold
    tau = min_lag
    while tau < max_lag:
        if cmndf[tau] < threshold:
            while tau + 1 < max_lag and cmndf[tau + 1] < cmndf[tau]:
                tau += 1
            break
        tau += 1
    else:
        search = cmndf[min_lag:max_lag]
        if search.size == 0:
            return None
        tau = int(np.argmin(search)) + min_lag
        if cmndf[tau] > 0.5:
            return None

    # Step 4: parabolic interpolation
    if 1 <= tau < max_lag - 1:
        y0, y1, y2 = float(cmndf[tau - 1]), float(cmndf[tau]), float(cmndf[tau + 1])
        denom = 2.0 * (2.0 * y1 - y0 - y2)
        if abs(denom) > 1e-12:
            tau = tau + (y2 - y0) / denom

    if tau <= 0:
        return None

    frequency = sample_rate / tau
    if frequency < min_freq or frequency > max_freq:
        return None

    return float(frequency)


def estimate_key_from_audio(
    samples: np.ndarray,
    sample_rate: int,
    frame_size: int = 4096,
    hop_size: int = 2048,
) -> tuple[str, str, float] | None:
    histogram = np.zeros(12, dtype=np.float32)
    x = np.asarray(samples, dtype=np.float32)
    if x.size < frame_size:
        return None

    for start in range(0, x.size - frame_size + 1, hop_size):
        frame = x[start : start + frame_size]
        frequency = detect_pitch_yin(frame, sample_rate)
        if frequency is None:
            frequency = detect_pitch_autocorrelation(frame, sample_rate)
        if frequency is None:
            continue
        midi = int(round(frequency_to_midi(frequency)))
        histogram[midi % 12] += float(np.sqrt(np.mean(frame * frame)))

    total = float(np.sum(histogram))
    if total <= 1e-6:
        return None

    histogram = histogram / total
    best_root = 0
    best_scale = "major"
    best_score = -1.0
    for root in range(12):
        for scale_name in ("major", "minor"):
            allowed = SCALES[scale_name]
            score = 0.0
            for pc, weight in enumerate(histogram):
                rel = (pc - root) % 12
                if rel in allowed:
                    score += float(weight)
                else:
                    score -= float(weight) * 0.35
            score += float(histogram[root]) * 0.25
            score += float(histogram[(root + 7) % 12]) * 0.12
            if score > best_score:
                best_root = root
                best_scale = scale_name
                best_score = score

    confidence = float(np.clip(best_score, 0.0, 1.0))
    return NOTE_NAMES[best_root], best_scale, confidence


def detect_pitch_autocorrelation(
    samples: np.ndarray,
    sample_rate: int,
    min_freq: float = 70.0,
    max_freq: float = 900.0,
) -> float | None:
    """Detect monophonic pitch with normalized autocorrelation."""
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim != 1 or x.size < int(sample_rate / min_freq):
        return None

    x = x - float(np.mean(x))
    rms = float(np.sqrt(np.mean(x * x)))
    if rms < 0.01:
        return None

    window = np.hanning(x.size).astype(np.float32)
    x = x * window
    corr = np.correlate(x, x, mode="full")[x.size - 1 :]
    if corr[0] <= 1e-9:
        return None
    corr = corr / corr[0]

    min_lag = max(1, int(sample_rate / max_freq))
    max_lag = min(corr.size - 2, int(sample_rate / min_freq))
    if max_lag <= min_lag:
        return None

    search = corr[min_lag:max_lag]
    lag = int(np.argmax(search)) + min_lag
    confidence = float(corr[lag])
    if confidence < 0.25:
        return None

    if 1 <= lag < corr.size - 1:
        y0, y1, y2 = corr[lag - 1], corr[lag], corr[lag + 1]
        denom = 2.0 * (2.0 * y1 - y0 - y2)
        if abs(float(denom)) > 1e-9:
            lag = lag + float((y2 - y0) / denom)

    return float(sample_rate / lag)


# ---------------------------------------------------------------------------
# Pitch trajectory smoother
# ---------------------------------------------------------------------------

class PitchSmoother:
    """Smooth pitch trajectory with median filter + IIR low-pass."""

    def __init__(self, history_size: int = 9, smoothing: float = 0.35) -> None:
        self.history: deque[float | None] = deque(maxlen=history_size)
        self.smoothing = smoothing
        self.current: float | None = None

    def process(self, frequency: float | None) -> float | None:
        self.history.append(frequency)

        valid = [f for f in self.history if f is not None]
        if not valid:
            return self.current

        median = float(np.median(valid))

        # octave jump rejection (symmetric around 2.0)
        if frequency is not None and self.current is not None:
            ratio = frequency / self.current
            if ratio > 1.75 or ratio < 0.57:
                frequency = median

        if self.current is None:
            self.current = median
        elif frequency is not None:
            self.current += (frequency - self.current) * self.smoothing

        return self.current

    def reset(self) -> None:
        self.history.clear()
        self.current = None


def nearest_allowed_note(
    frequency: float,
    root: str = "C",
    scale: str = "major",
) -> Note:
    root_pc = NOTE_NAMES.index(root)
    allowed = SCALES[scale]
    midi_float = frequency_to_midi(frequency)
    center = int(round(midi_float))

    candidates: list[int] = []
    for midi_note in range(center - 12, center + 13):
        if (midi_note - root_pc) % 12 in allowed:
            candidates.append(midi_note)

    best = min(candidates, key=lambda note: abs(note - midi_float))
    return Note(midi_note_name(best), best, midi_to_frequency(best))


def soft_limiter(samples: np.ndarray, drive: float = 1.2) -> np.ndarray:
    x = np.asarray(samples, dtype=np.float32) * drive
    return np.tanh(x).astype(np.float32)


# ---------------------------------------------------------------------------
# Parameter smoother for real-time control
# ---------------------------------------------------------------------------

class ParamSmoother:
    """Exponential smoother for a single float parameter."""

    def __init__(self, initial: float = 0.0, smoothing: float = 0.15) -> None:
        self.value = initial
        self.smoothing = smoothing

    def process(self, target: float) -> float:
        self.value += (target - self.value) * self.smoothing
        return self.value

    def set_immediate(self, value: float) -> None:
        self.value = value
