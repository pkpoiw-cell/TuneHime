"""WebSocket server for AI Live Tuner Electron frontend."""

from __future__ import annotations

import asyncio
import json
import sys
import threading
import queue
from pathlib import Path

import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import websockets
from websockets.asyncio.server import serve

from ai_live_tuner.audio_engine import RealtimeVoiceEngine, engine_available, process_offline_audio
from ai_live_tuner.dsp import NOTE_NAMES, estimate_key_from_audio
from ai_live_tuner.logging_setup import setup_logging
from ai_live_tuner.settings import (
    BUILT_IN_PRESETS, DEFAULT_CONFIG, load_state, merged_presets,
    preset_from_config, save_state, settings_path,
)

try:
    import sounddevice as sd
except ImportError:
    sd = None

SAMPLE_RATE = 48000
BLOCK_SIZE = 2048
PITCH_WINDOW = 4096
SCALE_LABELS = {"大调": "major", "小调": "minor", "半音阶": "chromatic"}
SCALE_TO_LABEL = {v: k for k, v in SCALE_LABELS.items()}


class AudioBackend:
    def __init__(self) -> None:
        self.logger = setup_logging()
        self.saved_state = load_state()
        self.user_presets = dict(self.saved_state["presets"])
        self.presets = merged_presets(self.user_presets)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(self.saved_state["config"])
        self.config = cfg
        self.engine = RealtimeVoiceEngine(SAMPLE_RATE, BLOCK_SIZE, PITCH_WINDOW)
        self.stop_event = threading.Event()
        self.audio_thread: threading.Thread | None = None
        self.stream = None
        self.input_devices: list[tuple[str, int | None]] = []
        self.output_devices: list[tuple[str, int | None]] = []
        self.status_queue: queue.Queue[dict] = queue.Queue(maxsize=16)
        self.test_original: np.ndarray | None = None
        self.test_processed: np.ndarray | None = None

    def load_devices(self) -> dict:
        if sd is None:
            return {"input": ["默认输入"], "output": ["默认输出"]}
        devices = sd.query_devices()
        self.input_devices = [("默认输入", None)]
        self.output_devices = [("默认输出", None)]
        for idx, dev in enumerate(devices):
            name = f"{idx}: {dev['name']}"
            if int(dev["max_input_channels"]) > 0:
                self.input_devices.append((name, idx))
            if int(dev["max_output_channels"]) > 0:
                self.output_devices.append((name, idx))
        return {
            "input": [n for n, _ in self.input_devices],
            "output": [n for n, _ in self.output_devices],
        }

    def _selected_device(self, values, selected):
        for name, index in values:
            if name == selected:
                return index
        return None

    def start(self) -> None:
        if sd is None:
            return
        if self.audio_thread and self.audio_thread.is_alive():
            return
        self.stop_event.clear()
        self.engine.reset()
        self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.audio_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.stream:
            self.stream.abort()
            self.stream.close()
            self.stream = None

    def _audio_worker(self) -> None:
        input_dev = self._selected_device(self.input_devices, self.config.get("input_device", ""))
        output_dev = self._selected_device(self.output_devices, self.config.get("output_device", ""))

        def callback(indata, outdata, frames, time_info, status):
            mono = indata[:, 0].astype(np.float32, copy=True)
            cfg = dict(self.config)
            cfg["scale"] = SCALE_LABELS.get(str(cfg["scale"]), str(cfg["scale"]))
            result = self.engine.process_block(mono, cfg)
            outdata[:] = result.audio.reshape(-1, 1)
            level = float(np.sqrt(np.mean(result.audio ** 2)))

            spec = np.zeros(32, dtype=np.float32)
            if result.audio.size >= 256:
                s = np.abs(np.fft.rfft(result.audio * np.hanning(result.audio.size)))
                freqs = np.fft.rfftfreq(result.audio.size, 1.0 / SAMPLE_RATE)
                mask = (freqs >= 80) & (freqs <= 8000)
                vocal = s[mask] if np.any(mask) else s[:32]
                chunk = max(1, vocal.size // 32)
                for i in range(32):
                    start = i * chunk
                    end = min(start + chunk, vocal.size)
                    spec[i] = float(np.mean(vocal[start:end]))

            cents = 0.0
            if result.note and result.frequency:
                from ai_live_tuner.dsp import frequency_to_midi
                cents = (frequency_to_midi(result.frequency) - result.note.midi) * 100.0

            try:
                self.status_queue.put_nowait({
                    "type": "status",
                    "frequency": result.frequency,
                    "target": result.note.name if result.note else "--",
                    "semitones": result.semitones,
                    "level": min(1.0, level * 3.0),
                    "cents": cents,
                    "spectrum": spec.tolist(),
                    "auto_status": result.auto_status,
                })
            except queue.Full:
                try:
                    self.status_queue.get_nowait()
                    self.status_queue.put_nowait({
                        "type": "status",
                        "frequency": result.frequency,
                        "target": result.note.name if result.note else "--",
                        "semitones": result.semitones,
                        "level": min(1.0, level * 3.0),
                        "cents": cents,
                        "spectrum": spec.tolist(),
                        "auto_status": result.auto_status,
                    })
                except (queue.Full, queue.Empty):
                    pass

        try:
            self.stream = sd.Stream(
                samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, dtype="float32",
                channels=1, device=(input_dev, output_dev),
                callback=callback, latency="low",
            )
            with self.stream:
                while not self.stop_event.wait(0.1):
                    pass
        except Exception as exc:
            self.logger.exception("Audio worker failed")
            try:
                self.status_queue.put_nowait({"type": "error", "text": str(exc)})
            except queue.Full:
                pass

    def record_test(self) -> str:
        if sd is None:
            return "缺少音频依赖"
        if self.audio_thread and self.audio_thread.is_alive():
            self.stop()
        input_dev = self._selected_device(self.input_devices, self.config.get("input_device", ""))
        try:
            rec = sd.rec(SAMPLE_RATE * 5, samplerate=SAMPLE_RATE, channels=1, dtype="float32", device=input_dev)
            sd.wait()
            original = rec[:, 0].astype(np.float32, copy=True)
            cfg = dict(self.config)
            cfg["scale"] = SCALE_LABELS.get(str(cfg["scale"]), str(cfg["scale"]))
            processed = process_offline_audio(original, cfg, SAMPLE_RATE, BLOCK_SIZE, PITCH_WINDOW)
            self.test_original = original
            self.test_processed = processed
            return "测试音频已生成，可以播放对比"
        except Exception as exc:
            return f"测试失败: {exc}"

    def play_test(self, kind: str) -> str:
        if sd is None:
            return "缺少音频依赖"
        data = self.test_original if kind == "original" else self.test_processed
        if data is None:
            return "请先录制"
        output_dev = self._selected_device(self.output_devices, self.config.get("output_device", ""))
        try:
            sd.play(data.reshape(-1, 1), samplerate=SAMPLE_RATE, device=output_dev)
            sd.wait()
            return "播放完成"
        except Exception as exc:
            return f"播放失败: {exc}"

    def play_ab(self) -> str:
        if self.test_original is None or self.test_processed is None:
            return "请先录制"
        silence = np.zeros(int(SAMPLE_RATE * 0.4), dtype=np.float32)
        combined = np.concatenate([self.test_original, silence, self.test_processed]).astype(np.float32)
        output_dev = self._selected_device(self.output_devices, self.config.get("output_device", ""))
        try:
            sd.play(combined.reshape(-1, 1), samplerate=SAMPLE_RATE, device=output_dev)
            sd.wait()
            return "播放完成"
        except Exception as exc:
            return f"播放失败: {exc}"

    def find_virtual(self) -> str:
        keywords = ("cable input", "vb-audio", "voicemeeter input", "virtual", "blackhole")
        for name, _ in self.output_devices:
            if any(kw in name.lower() for kw in keywords):
                self.config["output_device"] = name
                return f"已选择: {name}"
        return "未找到虚拟声卡，请先安装 VB-CABLE 或 Voicemeeter"

    def test_tone(self) -> str:
        if sd is None:
            return "缺少音频依赖"
        t = np.arange(int(SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE
        tone = (0.18 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
        output_dev = self._selected_device(self.output_devices, self.config.get("output_device", ""))
        try:
            sd.play(tone.reshape(-1, 1), samplerate=SAMPLE_RATE, device=output_dev)
            sd.wait()
            return "测试音播放完成"
        except Exception as exc:
            return f"播放失败: {exc}"

    def detect_key(self) -> dict | None:
        if sd is None:
            return None
        input_dev = self._selected_device(self.input_devices, self.config.get("input_device", ""))
        try:
            rec = sd.rec(SAMPLE_RATE * 5, samplerate=SAMPLE_RATE, channels=1, dtype="float32", device=input_dev)
            sd.wait()
            samples = rec[:, 0].astype(np.float32, copy=True)
            result = estimate_key_from_audio(samples, SAMPLE_RATE)
            if result:
                root, scale, conf = result
                self.config["root"] = root
                self.config["scale"] = SCALE_TO_LABEL.get(scale, "半音阶")
                return {"root": root, "scale": scale, "confidence": conf}
        except Exception:
            pass
        return None

    def apply_preset(self, name: str) -> None:
        preset = self.presets.get(name)
        if not preset:
            return
        for key in ("amount", "speed", "mix", "gate", "compression", "brightness", "gain", "deesser", "reverb"):
            if key in preset:
                self.config[key] = preset[key]
        self.config["preset"] = name

    def set_config(self, key: str, value) -> None:
        self.config[key] = value

    def save_settings(self) -> None:
        try:
            save_state(self.config, self.user_presets)
        except OSError:
            pass


# Global backend instance
backend = AudioBackend()


async def handler(websocket):
    """Handle WebSocket messages."""
    print(f"Client connected: {websocket.remote_address}")

    # Send initial devices
    devices = backend.load_devices()
    await websocket.send(json.dumps({"type": "devices", **devices}))

    async for raw in websocket:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue

        msg_type = msg.get("type")

        if msg_type == "get_devices":
            devices = backend.load_devices()
            await websocket.send(json.dumps({"type": "devices", **devices}))

        elif msg_type == "start":
            if msg.get("auto_mode"):
                backend.config["auto_mode"] = True
            backend.start()
            await websocket.send(json.dumps({"type": "auto_status", "text": "自动识别中：请正常唱歌，软件会边听边调整"}))

        elif msg_type == "stop":
            backend.stop()
            await websocket.send(json.dumps({"type": "auto_status", "text": "已停止"}))

        elif msg_type == "config":
            backend.set_config(msg["key"], msg["value"])

        elif msg_type == "apply_preset":
            backend.apply_preset(msg.get("name", ""))
            await websocket.send(json.dumps({"type": "auto_status", "text": f"已应用预设: {msg.get('name', '')}"}))

        elif msg_type == "detect_key":
            result = backend.detect_key()
            if result:
                await websocket.send(json.dumps({"type": "key_detected", **result}))
            else:
                await websocket.send(json.dumps({"type": "auto_status", "text": "未识别到稳定音高"}))

        elif msg_type == "record_test":
            text = backend.record_test()
            await websocket.send(json.dumps({"type": "test_status", "text": text}))

        elif msg_type == "play_test":
            text = backend.play_test(msg.get("kind", "original"))
            await websocket.send(json.dumps({"type": "test_status", "text": text}))

        elif msg_type == "play_ab":
            text = backend.play_ab()
            await websocket.send(json.dumps({"type": "test_status", "text": text}))

        elif msg_type == "find_virtual":
            text = backend.find_virtual()
            await websocket.send(json.dumps({"type": "route_status", "text": text}))

        elif msg_type == "test_tone":
            text = backend.test_tone()
            await websocket.send(json.dumps({"type": "route_status", "text": text}))

    print("Client disconnected")


async def status_broadcaster(websockets_list):
    """Broadcast audio status to all connected clients."""
    while True:
        try:
            while not backend.status_queue.empty():
                msg = backend.status_queue.get_nowait()
                data = json.dumps(msg)
                for ws in list(websockets_list):
                    try:
                        await ws.send(data)
                    except Exception:
                        pass
        except queue.Empty:
            pass
        await asyncio.sleep(0.05)  # 20Hz update rate


async def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9876
    connected = set()

    async with serve(handler, "127.0.0.1", port) as server:
        print(f"WebSocket server running on ws://127.0.0.1:{port}")
        # Start broadcaster
        broadcaster = asyncio.create_task(status_broadcaster(connected))
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
