from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

APP_NAME = "LocalDictation"

DEFAULT_SETTINGS: dict[str, Any] = {
    "config_version": 2,
    "hotkey": "ctrl+alt+space",
    "recording": {
        "sample_rate": 16000,
        "channels": 1,
        "max_seconds": 120,
        "silence_stop": {
            "enabled": True,
            "min_recording_seconds": 1.5,
            "speech_threshold": 0.012,
            "silence_seconds": 1.4,
        },
    },
    "stt": {
        "engine": "faster-whisper",
        "model": "base.en",
        "device": "cpu",
        "compute_type": "int8",
        "language": "en",
        "vad_filter": True,
        "local_files_only": False,
    },
    "cleanup": {
        "enabled": False,
        "provider": "ollama",
        "endpoint": "http://localhost:11434/api/generate",
        "model": "gemma3:1b",
        "mode": "punctuate",
        "timeout_seconds": 20,
    },
    "insertion": {
        "mode": "auto",
        "restore_clipboard_text": True,
        "focus_restore_timeout_ms": 700,
        "direct_typing_delay_ms": 1,
        "clipboard_fallback": True,
        "preserve_clipboard_formats": True,
        "copy_on_failure": True,
    },
    "setup": {
        "stt_model_ready": False,
        "ollama_install": "auto",
        "ollama_ready": False,
        "last_bootstrap_status": None,
    },
    "startup": {"enabled": False},
    "logging": {"level": "INFO", "keep_files": 5},
}


class SettingsError(RuntimeError):
    """Raised when settings cannot be read or written."""


def app_data_dir() -> Path:
    root = os.environ.get("APPDATA")
    if root:
        return Path(root) / APP_NAME
    return Path.home() / "AppData" / "Roaming" / APP_NAME


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def logs_dir() -> Path:
    return app_data_dir() / "logs"


def deep_merge(defaults: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(defaults)
    for key, value in loaded.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def default_settings() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_SETTINGS)


def migrate_settings(loaded: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(loaded)
    version = int(migrated.get("config_version", 1))
    if version < 2:
        insertion = migrated.setdefault("insertion", {})
        if insertion.get("mode") == "clipboard":
            insertion["mode"] = "auto"
        migrated["config_version"] = 2
    return migrated


def load_settings(path: Path | str | None = None, create: bool = True) -> dict[str, Any]:
    target = Path(path) if path else settings_path()
    if not target.exists():
        settings = default_settings()
        if create:
            save_settings(settings, target)
        return settings

    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SettingsError(f"Settings file is not valid JSON: {target}") from exc
    except OSError as exc:
        raise SettingsError(f"Could not read settings file: {target}") from exc

    if not isinstance(loaded, dict):
        raise SettingsError(f"Settings file must contain a JSON object: {target}")

    loaded = migrate_settings(loaded)
    merged = deep_merge(DEFAULT_SETTINGS, loaded)
    if create and merged != loaded:
        save_settings(merged, target)
    return merged


def save_settings(settings: dict[str, Any], path: Path | str | None = None) -> Path:
    target = Path(path) if path else settings_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise SettingsError(f"Could not write settings file: {target}") from exc
    return target
