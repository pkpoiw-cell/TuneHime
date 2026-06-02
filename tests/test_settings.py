import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from ai_live_tuner.settings import BUILT_IN_PRESETS, DEFAULT_CONFIG, load_state, save_state, settings_path


class SettingsTests(unittest.TestCase):
    def test_save_and_load_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            save_state(
                {
                    "root": "D",
                    "scale": "minor",
                    "amount": 0.4,
                    "speed": 0.2,
                    "mix": 0.6,
                    "gate": 0.3,
                    "compression": 0.5,
                    "brightness": 0.7,
                    "gain": 1.1,
                    "bypass": True,
                    "deesser": 0.45,
                    "reverb": 0.22,
                    "preset": "My Preset",
                    "input_device": "Mic",
                    "output_device": "Cable",
                },
                {"My Preset": {"amount": 0.4, "speed": 0.2, "mix": 0.6}},
                path,
            )

            state = load_state(path)

        self.assertEqual(state["config"]["root"], "D")
        self.assertEqual(state["config"]["scale"], "小调")
        self.assertTrue(state["config"]["bypass"])
        self.assertAlmostEqual(state["config"]["deesser"], 0.45, places=2)
        self.assertAlmostEqual(state["config"]["reverb"], 0.22, places=2)
        self.assertIn("My Preset", state["presets"])

    def test_built_in_presets_are_not_overwritten_by_user_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            save_state({}, {"Pop": {"amount": 0.1}}, path)
            state = load_state(path)

        self.assertNotIn("Pop", state["presets"])
        self.assertIn("流行", BUILT_IN_PRESETS)

    def test_data_directory_can_be_overridden(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict("os.environ", {"AI_LIVE_TUNER_DATA": folder}):
                self.assertEqual(settings_path().parent, Path(folder))

    def test_default_config_has_new_params(self) -> None:
        self.assertIn("deesser", DEFAULT_CONFIG)
        self.assertIn("reverb", DEFAULT_CONFIG)
        self.assertEqual(DEFAULT_CONFIG["deesser"], 0.30)
        self.assertEqual(DEFAULT_CONFIG["reverb"], 0.15)

    def test_built_in_presets_have_new_params(self) -> None:
        for name, preset in BUILT_IN_PRESETS.items():
            self.assertIn("deesser", preset, f"{name} missing deesser")
            self.assertIn("reverb", preset, f"{name} missing reverb")
            self.assertGreaterEqual(preset["deesser"], 0.0)
            self.assertLessEqual(preset["deesser"], 1.0)
            self.assertGreaterEqual(preset["reverb"], 0.0)
            self.assertLessEqual(preset["reverb"], 1.0)

    def test_missing_new_params_use_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            # save without new params
            save_state(
                {"root": "C", "amount": 0.5, "speed": 0.3, "mix": 0.7,
                 "gate": 0.2, "compression": 0.4, "brightness": 0.3,
                 "gain": 1.0, "bypass": False, "preset": "test"},
                {},
                path,
            )
            state = load_state(path)
        # should have defaults
        self.assertAlmostEqual(state["config"]["deesser"], 0.30, places=2)
        self.assertAlmostEqual(state["config"]["reverb"], 0.15, places=2)


if __name__ == "__main__":
    unittest.main()
