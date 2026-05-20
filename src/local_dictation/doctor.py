from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path

from .cleanup import check_ollama
from .config import load_settings, logs_dir, settings_path
from .hotkey import HotkeyError, parse_hotkey
from .recorder import apply_gain, parse_input_device_id


def _module_status(module: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module)
        return True, "imported"
    except Exception as exc:
        return False, str(exc)


def _configured_input_device_id(settings: dict) -> int | None:
    return parse_input_device_id(settings.get("recording", {}).get("input_device_id"))


def _microphone_probe(sd, np, settings: dict) -> tuple[float, float]:
    recording = settings.get("recording", {})
    sample_rate = int(recording.get("sample_rate", 16000))
    channels = int(recording.get("channels", 1))
    gain_db = float(recording.get("gain_db", 0.0))
    device_id = _configured_input_device_id(settings)
    frame_count = max(1, int(sample_rate * 0.35))
    audio = sd.rec(frame_count, samplerate=sample_rate, channels=channels, dtype="float32", device=device_id)
    sd.wait()
    adjusted = apply_gain(audio, gain_db, np_module=np)
    rms = float(np.sqrt(np.mean(np.square(adjusted)))) if getattr(adjusted, "size", 0) else 0.0
    peak = float(np.max(np.abs(adjusted))) if getattr(adjusted, "size", 0) else 0.0
    return rms, peak


def run_doctor() -> int:
    ok = True
    lines: list[str] = []
    lines.append("Local Dictation doctor")
    lines.append(f"Python: {sys.version.split()[0]} ({platform.architecture()[0]})")
    if sys.version_info[:2] != (3, 12):
        ok = False
        lines.append("FAIL Python 3.12 is required for the pinned MVP dependencies.")
    else:
        lines.append("OK Python version is supported.")

    try:
        settings = load_settings(create=True)
        lines.append(f"OK Settings: {settings_path()}")
    except Exception as exc:
        ok = False
        settings = {}
        lines.append(f"FAIL Settings could not be loaded: {exc}")

    log_path = logs_dir()
    try:
        log_path.mkdir(parents=True, exist_ok=True)
        lines.append(f"OK Logs: {log_path}")
    except Exception as exc:
        ok = False
        lines.append(f"FAIL Log directory could not be created: {exc}")

    required_modules = {
        "faster_whisper": "faster-whisper",
        "sounddevice": "sounddevice",
        "numpy": "numpy",
        "win32gui": "pywin32",
        "win32clipboard": "pywin32",
        "pystray": "pystray",
        "PIL": "Pillow",
    }
    module_results: dict[str, bool] = {}
    for module, package in required_modules.items():
        available, message = _module_status(module)
        module_results[module] = available
        if available:
            lines.append(f"OK Import {package}")
        else:
            ok = False
            lines.append(f"FAIL Could not import {package} ({module}): {message}")

    try:
        binding = parse_hotkey(str(settings.get("hotkey", "")))
        lines.append(f"OK Hotkey parses as {binding.normalized}")
    except HotkeyError as exc:
        ok = False
        lines.append(f"FAIL Hotkey is invalid: {exc}")

    if module_results.get("sounddevice", False):
        try:
            import sounddevice as sd

            device = sd.query_devices(kind="input")
            lines.append(f"OK Default microphone: {device.get('name', 'unknown')}")
            devices = sd.query_devices()
            input_devices = [
                (index, candidate)
                for index, candidate in enumerate(devices)
                if int(candidate.get("max_input_channels", 0)) > 0
            ]
            lines.append(f"INFO Input devices found: {len(input_devices)}")
            for index, candidate in input_devices[:10]:
                lines.append(
                    "INFO Input device "
                    f"{index}: {candidate.get('name', 'unknown')} "
                    f"({candidate.get('max_input_channels', 0)} channels)"
                )
            if len(input_devices) > 10:
                lines.append(f"INFO Input devices omitted: {len(input_devices) - 10}")
            try:
                configured_device = _configured_input_device_id(settings)
                recording = settings.get("recording", {})
                silence = recording.get("silence_stop", {})
                lines.append(f"INFO Recording input device setting: {configured_device if configured_device is not None else 'default'}")
                lines.append(
                    "INFO Microphone sensitivity: "
                    f"gain {float(recording.get('gain_db', 0.0)):g} dB, "
                    f"speech threshold {float(silence.get('speech_threshold', 0.012)):g}"
                )
                if module_results.get("numpy", False):
                    import numpy as np

                    rms, peak = _microphone_probe(sd, np, settings)
                    lines.append(f"INFO Microphone RMS probe: rms={rms:.6f}, peak={peak:.6f} after configured gain")
            except Exception as exc:
                lines.append(f"WARN Microphone RMS probe could not run: {exc}")
        except Exception as exc:
            ok = False
            lines.append(f"FAIL Default microphone unavailable: {exc}")
    else:
        lines.append("SKIP Microphone check because sounddevice is missing.")

    stt = settings.get("stt", {})
    lines.append(f"INFO STT model setting: {stt.get('model', 'base.en')}")
    lines.append(f"INFO Insertion mode: {settings.get('insertion', {}).get('mode', 'auto')}")
    setup = settings.get("setup", {})
    lines.append(f"INFO STT model ready flag: {setup.get('stt_model_ready', False)}")

    cleanup = settings.get("cleanup", {})
    if cleanup.get("enabled", False):
        reachable, message = check_ollama(
            cleanup.get("endpoint", "http://localhost:11434/api/generate"),
            timeout_seconds=2,
        )
        if reachable:
            lines.append(f"OK {message}")
        else:
            ok = False
            lines.append(f"FAIL {message}")
    else:
        lines.append("OK Cleanup is disabled; Ollama is optional.")

    if sys.platform == "win32":
        try:
            from .startup import startup_command

            command = startup_command()
            lines.append(f"INFO Startup command: {command or 'not enabled'}")
        except Exception as exc:
            lines.append(f"WARN Startup status could not be read: {exc}")

    print("\n".join(lines))
    return 0 if ok else 1


def settings_file() -> Path:
    return settings_path()
