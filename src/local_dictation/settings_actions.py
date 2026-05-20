from __future__ import annotations

import copy
from typing import Any

from .hotkey import parse_hotkey

VALID_INSERTION_MODES = {"auto", "direct", "typing", "clipboard"}
MIN_GAIN_DB = -12.0
MAX_GAIN_DB = 24.0


def required_text(value: str, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text


def positive_float(value: str, field_name: str) -> float:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    try:
        parsed = float(text)
    except ValueError:
        raise ValueError(f"{field_name} must be a number.") from None
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than 0.")
    return parsed


def float_in_range(value: str, field_name: str, minimum: float, maximum: float) -> float:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    try:
        parsed = float(text)
    except ValueError:
        raise ValueError(f"{field_name} must be a number.") from None
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name} must be between {minimum:g} and {maximum:g}.")
    return parsed


def optional_device_id(value: str, field_name: str = "Input device") -> int | None:
    text = value.strip()
    if not text or text.lower() == "default":
        return None
    device_text = text.split(":", 1)[0].strip()
    try:
        parsed = int(device_text)
    except ValueError:
        raise ValueError(f"{field_name} must be default or a numeric device id.") from None
    if parsed < 0:
        raise ValueError(f"{field_name} must be default or a non-negative device id.")
    return parsed


def update_core_settings(
    settings: dict[str, Any],
    *,
    hotkey: str,
    stt_model: str,
    cleanup_enabled: bool,
    cleanup_model: str,
) -> dict[str, Any]:
    updated = copy.deepcopy(settings)
    updated["hotkey"] = parse_hotkey(required_text(hotkey, "Hotkey")).normalized
    updated.setdefault("stt", {})["model"] = required_text(stt_model, "Speech model")
    cleanup = updated.setdefault("cleanup", {})
    cleanup["enabled"] = bool(cleanup_enabled)
    cleanup["model"] = required_text(cleanup_model, "Ollama model")
    return updated


def update_settings(
    settings: dict[str, Any],
    *,
    hotkey: str,
    stt_model: str,
    cleanup_enabled: bool,
    cleanup_model: str,
    insertion_mode: str,
    input_device_id: str = "default",
    gain_db: str = "0",
    silence_enabled: bool,
    silence_seconds: str,
    speech_threshold: str,
    startup_enabled: bool,
) -> dict[str, Any]:
    updated = update_core_settings(
        settings,
        hotkey=hotkey,
        stt_model=stt_model,
        cleanup_enabled=cleanup_enabled,
        cleanup_model=cleanup_model,
    )
    normalized_insertion_mode = required_text(insertion_mode, "Insertion mode").lower()
    if normalized_insertion_mode not in VALID_INSERTION_MODES:
        raise ValueError("Insertion mode must be auto, direct, typing, or clipboard.")

    updated.setdefault("insertion", {})["mode"] = normalized_insertion_mode
    recording = updated.setdefault("recording", {})
    recording["input_device_id"] = optional_device_id(input_device_id)
    recording["gain_db"] = float_in_range(gain_db, "Microphone gain", MIN_GAIN_DB, MAX_GAIN_DB)
    silence = recording.setdefault("silence_stop", {})
    silence["enabled"] = bool(silence_enabled)
    silence["silence_seconds"] = positive_float(silence_seconds, "Silence seconds")
    silence["speech_threshold"] = positive_float(speech_threshold, "Speech threshold")
    updated.setdefault("startup", {})["enabled"] = bool(startup_enabled)
    return updated