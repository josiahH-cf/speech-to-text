from __future__ import annotations

import copy
from typing import Any

from .hotkey import parse_hotkey

VALID_INSERTION_MODES = {"auto", "direct", "typing", "clipboard"}


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
    silence = updated.setdefault("recording", {}).setdefault("silence_stop", {})
    silence["enabled"] = bool(silence_enabled)
    silence["silence_seconds"] = positive_float(silence_seconds, "Silence seconds")
    silence["speech_threshold"] = positive_float(speech_threshold, "Speech threshold")
    updated.setdefault("startup", {})["enabled"] = bool(startup_enabled)
    return updated