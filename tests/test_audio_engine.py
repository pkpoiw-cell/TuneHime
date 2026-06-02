import unittest

import numpy as np

from ai_live_tuner.audio_engine import AutoAdjustState, RealtimeVoiceEngine, engine_available, process_offline_audio


def sine(freq: float, seconds: float = 0.12, sample_rate: int = 48000) -> np.ndarray:
    t = np.arange(int(seconds * sample_rate), dtype=np.float32) / sample_rate
    return (0.5 * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)


FULL_CONFIG = {
    "root": "C",
    "scale": "major",
    "amount": 0.8,
    "speed": 0.5,
    "mix": 0.9,
    "gate": 0.2,
    "compression": 0.4,
    "brightness": 0.3,
    "gain": 1.0,
    "bypass": False,
    "deesser": 0.3,
    "reverb": 0.15,
}


class AudioEngineTests(unittest.TestCase):
    def test_engine_processes_block(self) -> None:
        engine = RealtimeVoiceEngine(48000, 1024, 4096)
        result = engine.process_block(sine(450.0, seconds=1024 / 48000), FULL_CONFIG)
        self.assertEqual(result.audio.shape, (1024,))
        self.assertEqual(result.audio.dtype, np.float32)
        self.assertEqual(result.engine, "专业引擎")

    def test_offline_processing_keeps_length(self) -> None:
        samples = sine(330.0)
        processed = process_offline_audio(samples, FULL_CONFIG, 48000, 1024, 4096)
        self.assertEqual(processed.shape, samples.shape)
        self.assertEqual(processed.dtype, np.float32)

    def test_engine_name_is_user_visible(self) -> None:
        self.assertEqual(engine_available(), "专业引擎")

    def test_quality_block_pitch_correction_moves_toward_target(self) -> None:
        from ai_live_tuner.dsp import detect_pitch_yin

        config = dict(FULL_CONFIG)
        config["amount"] = 1.0
        config["speed"] = 1.0
        config["mix"] = 1.0
        config["gate"] = 0.0
        config["compression"] = 0.0
        config["brightness"] = 0.0

        samples = sine(270.0, seconds=3.0)
        processed = process_offline_audio(samples, config, 48000, 4096, 8192)
        before = detect_pitch_yin(samples[48000 : 48000 + 4096], 48000)
        after = detect_pitch_yin(processed[48000 : 48000 + 4096], 48000)
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        assert before is not None
        assert after is not None
        self.assertLess(abs(after - 261.63), abs(before - 261.63))

    def test_professional_chain_gate_reduces_noise(self) -> None:
        """Quiet noise with high gate should be attenuated vs loud signal."""
        rng = np.random.default_rng(7)
        # quiet noise
        quiet = (0.003 * rng.normal(size=48000)).astype(np.float32)
        # loud signal
        loud = sine(330.0, seconds=1.0)

        config = dict(FULL_CONFIG)
        config["amount"] = 0.0
        config["mix"] = 0.0
        config["gate"] = 0.7
        config["compression"] = 0.0
        config["brightness"] = 0.0
        config["gain"] = 1.0
        config["reverb"] = 0.0

        processed_quiet = process_offline_audio(quiet, config, 48000, 4096, 8192)
        processed_loud = process_offline_audio(loud, config, 48000, 4096, 8192)

        rms_quiet = float(np.sqrt(np.mean(processed_quiet ** 2)))
        rms_loud = float(np.sqrt(np.mean(processed_loud ** 2)))
        # gate should make quiet signal much quieter than loud signal
        self.assertLess(rms_quiet, rms_loud * 0.5)

    def test_auto_adjust_updates_config(self) -> None:
        auto = AutoAdjustState(48000, 4096)
        config = dict(FULL_CONFIG)
        config["auto_mode"] = True
        config["amount"] = 0.4
        config["speed"] = 0.2
        result = auto.process(sine(440.0, seconds=1024 / 48000), config)
        self.assertTrue(result.status.startswith("自动："))
        self.assertGreater(result.config["amount"], config["amount"])
        self.assertIn(result.config["scale"], ("major", "minor"))

    def test_bypass_mode_returns_dry_signal(self) -> None:
        engine = RealtimeVoiceEngine(48000, 1024, 4096)
        config = dict(FULL_CONFIG)
        config["bypass"] = True
        block = sine(440.0, seconds=1024 / 48000)
        result = engine.process_block(block, config)
        np.testing.assert_array_equal(result.audio, block)
        self.assertEqual(result.semitones, 0.0)


if __name__ == "__main__":
    unittest.main()
