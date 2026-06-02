from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


APP_NAME = "AI Live Tuner"

DEFAULT_CONFIG: dict[str, Any] = {
    "root": "C",
    "scale": "大调",
    "amount": 0.70,
    "speed": 0.25,
    "mix": 0.80,
    "gate": 0.25,
    "compression": 0.40,
    "brightness": 0.25,
    "gain": 1.00,
    "bypass": False,
    "auto_mode": True,
    "deesser": 0.30,
    "reverb": 0.15,
    "preset": "流行",
    "input_device": "默认输入",
    "output_device": "默认输出",
}

BUILT_IN_PRESETS: dict[str, dict[str, float]] = {
    "自然": {
        "amount": 0.45,
        "speed": 0.16,
        "mix": 0.65,
        "gate": 0.25,
        "compression": 0.35,
        "brightness": 0.25,
        "gain": 1.00,
        "deesser": 0.20,
        "reverb": 0.10,
    },
    "流行": {
        "amount": 0.72,
        "speed": 0.30,
        "mix": 0.82,
        "gate": 0.35,
        "compression": 0.58,
        "brightness": 0.48,
        "gain": 1.04,
        "deesser": 0.35,
        "reverb": 0.18,
    },
    "电音": {
        "amount": 1.00,
        "speed": 0.85,
        "mix": 1.00,
        "gate": 0.45,
        "compression": 0.70,
        "brightness": 0.55,
        "gain": 1.00,
        "deesser": 0.15,
        "reverb": 0.05,
    },
}

LEGACY_PRESET_NAMES = {
    "Natural": "自然",
    "Pop": "流行",
    "Electric": "电音",
}

LEGACY_SCALE_NAMES = {
    "major": "大调",
    "minor": "小调",
    "chromatic": "半音阶",
}

LEGACY_DEVICE_NAMES = {
    "Default input": "默认输入",
    "Default output": "默认输出",
}


def app_data_dir() -> Path:
    override = os.environ.get("AI_LIVE_TUNER_DATA")
    if override:
        return Path(override)
    root = os.environ.get("APPDATA")
    if root:
        return Path(root) / "AI Live Tuner"
    return Path.home() / ".ai_live_tuner"


def log_dir() -> Path:
    path = writable_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return writable_app_data_dir() / "settings.json"


def writable_app_data_dir() -> Path:
    preferred = app_data_dir()
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "AI Live Tuner"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def load_state(path: Path | None = None) -> dict[str, Any]:
    file_path = path or settings_path()
    state: dict[str, Any] = {"config": dict(DEFAULT_CONFIG), "presets": {}}
    if not file_path.exists():
        return state

    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return state

    if isinstance(raw.get("config"), dict):
        state["config"].update(_sanitize_config(raw["config"]))
    if isinstance(raw.get("presets"), dict):
        state["presets"] = _sanitize_presets(raw["presets"])
    return state


def save_state(config: dict[str, Any], user_presets: dict[str, dict[str, float]], path: Path | None = None) -> Path:
    file_path = path or settings_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": _sanitize_config(config),
        "presets": _sanitize_presets(user_presets),
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path


def merged_presets(user_presets: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    presets = {name: dict(values) for name, values in BUILT_IN_PRESETS.items()}
    presets.update(_sanitize_presets(user_presets))
    return presets


def preset_from_config(config: dict[str, Any]) -> dict[str, float]:
    return {
        "amount": float(config["amount"]),
        "speed": float(config["speed"]),
        "mix": float(config["mix"]),
        "gate": float(config["gate"]),
        "compression": float(config["compression"]),
        "brightness": float(config["brightness"]),
        "gain": float(config["gain"]),
        "deesser": float(config.get("deesser", 0.3)),
        "reverb": float(config.get("reverb", 0.15)),
    }


def _sanitize_config(config: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(DEFAULT_CONFIG)
    for key in ("root", "scale", "preset", "input_device", "output_device"):
        if isinstance(config.get(key), str):
            sanitized[key] = config[key]
    sanitized["preset"] = LEGACY_PRESET_NAMES.get(sanitized["preset"], sanitized["preset"])
    sanitized["scale"] = LEGACY_SCALE_NAMES.get(sanitized["scale"], sanitized["scale"])
    sanitized["input_device"] = LEGACY_DEVICE_NAMES.get(sanitized["input_device"], sanitized["input_device"])
    sanitized["output_device"] = LEGACY_DEVICE_NAMES.get(sanitized["output_device"], sanitized["output_device"])
    for key in ("amount", "speed", "mix", "gate", "compression", "brightness", "deesser", "reverb"):
        sanitized[key] = _clamp_float(config.get(key), 0.0, 1.0, sanitized[key])
    sanitized["gain"] = _clamp_float(config.get("gain"), 0.2, 2.0, sanitized["gain"])
    if isinstance(config.get("bypass"), bool):
        sanitized["bypass"] = config["bypass"]
    if isinstance(config.get("auto_mode"), bool):
        sanitized["auto_mode"] = config["auto_mode"]
    return sanitized


def _sanitize_presets(presets: dict[str, Any]) -> dict[str, dict[str, float]]:
    sanitized: dict[str, dict[str, float]] = {}
    for name, values in presets.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(values, dict):
            continue
        name = LEGACY_PRESET_NAMES.get(name, name)
        if name in BUILT_IN_PRESETS:
            continue
        config = dict(DEFAULT_CONFIG)
        config.update(values)
        sanitized[name.strip()] = preset_from_config(_sanitize_config(config))
    return sanitized


def _clamp_float(value: Any, low: float, high: float, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return float(min(high, max(low, number)))
