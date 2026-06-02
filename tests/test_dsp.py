import math
import unittest

import numpy as np

from ai_live_tuner.dsp import (
    ParamSmoother,
    PitchSmoother,
    detect_pitch_autocorrelation,
    detect_pitch_yin,
    estimate_key_from_audio,
    frequency_to_midi,
    midi_note_name,
    midi_to_frequency,
    nearest_allowed_note,
    soft_limiter,
)


def sine(freq: float, seconds: float = 0.12, sample_rate: int = 48000) -> np.ndarray:
    t = np.arange(int(seconds * sample_rate), dtype=np.float32) / sample_rate
    return (0.6 * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)


class DspTests(unittest.TestCase):
    def test_detect_pitch_autocorrelation_finds_a4(self) -> None:
        detected = detect_pitch_autocorrelation(sine(440.0), 48000)
        self.assertIsNotNone(detected)
        assert detected is not None
        self.assertLess(abs(detected - 440.0), 3.0)

    def test_detect_pitch_yin_finds_a4(self) -> None:
        detected = detect_pitch_yin(sine(440.0), 48000)
        self.assertIsNotNone(detected)
        assert detected is not None
        self.assertLess(abs(detected - 440.0), 3.0)

    def test_detect_pitch_yin_finds_low_freq(self) -> None:
        detected = detect_pitch_yin(sine(110.0, seconds=0.2), 48000)
        self.assertIsNotNone(detected)
        assert detected is not None
        self.assertLess(abs(detected - 110.0), 5.0)

    def test_detect_pitch_yin_returns_none_for_silence(self) -> None:
        silence = np.zeros(4096, dtype=np.float32)
        self.assertIsNone(detect_pitch_yin(silence, 48000))

    def test_detect_pitch_yin_returns_none_for_short_input(self) -> None:
        short = np.zeros(10, dtype=np.float32)
        self.assertIsNone(detect_pitch_yin(short, 48000))

    def test_nearest_allowed_note_in_c_major(self) -> None:
        note = nearest_allowed_note(450.0, root="C", scale="major")
        self.assertEqual(note.name, "A4")
        self.assertTrue(math.isclose(note.frequency, midi_to_frequency(69), rel_tol=0.001))

    def test_estimate_key_from_audio_detects_c_major(self) -> None:
        notes = [261.63, 329.63, 392.0, 523.25]
        samples = np.concatenate([sine(freq, seconds=0.16) for freq in notes]).astype(np.float32)
        result = estimate_key_from_audio(samples, 48000)
        self.assertIsNotNone(result)
        assert result is not None
        root, scale, confidence = result
        self.assertEqual(root, "C")
        self.assertEqual(scale, "major")
        self.assertGreater(confidence, 0.2)


class FrequencyMidiTests(unittest.TestCase):
    def test_midi_to_frequency_a4(self) -> None:
        self.assertAlmostEqual(midi_to_frequency(69), 440.0, places=1)

    def test_midi_to_frequency_c4(self) -> None:
        self.assertAlmostEqual(midi_to_frequency(60), 261.63, places=1)

    def test_frequency_to_midi_a4(self) -> None:
        self.assertAlmostEqual(frequency_to_midi(440.0), 69.0, places=1)

    def test_midi_note_name_a4(self) -> None:
        self.assertEqual(midi_note_name(69), "A4")

    def test_midi_note_name_c4(self) -> None:
        self.assertEqual(midi_note_name(60), "C4")

    def test_midi_note_name_c_minus1(self) -> None:
        self.assertEqual(midi_note_name(0), "C-1")


class SoftLimiterTests(unittest.TestCase):
    def test_soft_limiter_passthrough_at_low_levels(self) -> None:
        signal = np.array([0.01, -0.01, 0.0], dtype=np.float32)
        output = soft_limiter(signal, drive=1.0)
        np.testing.assert_allclose(output, signal, atol=0.001)

    def test_soft_limiter_clips_at_high_levels(self) -> None:
        signal = np.array([2.0, -2.0, 5.0], dtype=np.float32)
        output = soft_limiter(signal, drive=1.0)
        self.assertLess(float(np.max(np.abs(output))), 1.01)

    def test_soft_limiter_keeps_dtype(self) -> None:
        signal = np.ones(100, dtype=np.float32)
        output = soft_limiter(signal)
        self.assertEqual(output.dtype, np.float32)

    def test_soft_limiter_drive_affects_clipping(self) -> None:
        signal = np.array([0.5], dtype=np.float32)
        low_drive = soft_limiter(signal, drive=1.0)
        high_drive = soft_limiter(signal, drive=3.0)
        self.assertGreater(float(high_drive[0]), float(low_drive[0]))


class PitchSmootherTests(unittest.TestCase):
    def test_smooth_returns_frequency(self) -> None:
        smoother = PitchSmoother(history_size=5, smoothing=0.5)
        result = smoother.process(440.0)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result, 440.0, delta=5.0)

    def test_smooth_tracks_gradual_change(self) -> None:
        smoother = PitchSmoother(history_size=5, smoothing=0.5)
        for freq in [440.0, 441.0, 442.0, 443.0, 444.0]:
            result = smoother.process(freq)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result, 444.0, delta=5.0)

    def test_smooth_rejects_octave_jump(self) -> None:
        smoother = PitchSmoother(history_size=5, smoothing=0.3)
        for _ in range(5):
            smoother.process(440.0)
        result = smoother.process(880.0)  # octave jump
        self.assertIsNotNone(result)
        assert result is not None
        self.assertLess(result, 600.0)

    def test_smooth_handles_none(self) -> None:
        smoother = PitchSmoother(history_size=5, smoothing=0.5)
        smoother.process(440.0)
        result = smoother.process(None)
        self.assertIsNotNone(result)

    def test_smooth_reset(self) -> None:
        smoother = PitchSmoother(history_size=5, smoothing=0.5)
        smoother.process(440.0)
        smoother.process(441.0)
        smoother.reset()
        self.assertIsNone(smoother.current)
        self.assertEqual(len(smoother.history), 0)


class ParamSmootherTests(unittest.TestCase):
    def test_smoother_converges(self) -> None:
        sm = ParamSmoother(initial=0.0, smoothing=0.5)
        for _ in range(20):
            result = sm.process(1.0)
        self.assertAlmostEqual(result, 1.0, delta=0.01)

    def test_set_immediate(self) -> None:
        sm = ParamSmoother(initial=0.0, smoothing=0.1)
        sm.set_immediate(1.0)
        self.assertAlmostEqual(sm.value, 1.0)


if __name__ == "__main__":
    unittest.main()
