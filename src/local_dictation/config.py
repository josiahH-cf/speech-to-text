from __future__ import annotations

import copy
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

APP_NAME = "LocalDictation"
KNOWN_STT_MODELS = ("tiny.en", "base.en", "small.en", "medium.en")

DEFAULT_SETTINGS: dict[str, Any] = {
    "config_version": 3,
    "hotkey": "ctrl+alt+space",
    "recording": {
        "sample_rate": 16000,
        "channels": 1,
        "max_seconds": 120,
        "cue_tone": "off",
        "input_device_id": None,
        "gain_db": 0.0,
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
    "gui": {"port": 8765},
}


class SettingsError(RuntimeError):
    """Raised when settings cannot be read or written."""


@dataclass(frozen=True)
class CleanupResult:
    path: Path
    removed: bool
    message: str


def app_data_dir() -> Path:
    root = os.environ.get("APPDATA")
    if root:
        return Path(root) / APP_NAME
    return Path.home() / "AppData" / "Roaming" / APP_NAME


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def logs_dir() -> Path:
    return app_data_dir() / "logs"


def huggingface_hub_cache_dir() -> Path:
    explicit_cache = os.environ.get("HUGGINGFACE_HUB_CACHE")
    if explicit_cache:
        return Path(explicit_cache)
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        return Path(hf_home) / "hub"
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home:
        return Path(xdg_cache_home) / "huggingface" / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def stt_model_cache_paths(models: tuple[str, ...] = KNOWN_STT_MODELS) -> tuple[Path, ...]:
    hub = huggingface_hub_cache_dir()
    paths: list[Path] = []
    for model in models:
        cache_name = f"models--Systran--faster-whisper-{model}"
        paths.append(hub / cache_name)
        paths.append(hub / ".locks" / cache_name)
    return tuple(dict.fromkeys(paths))


def cleanup_paths(paths: tuple[Path, ...], *, dry_run: bool = False) -> tuple[CleanupResult, ...]:
    results: list[CleanupResult] = []
    for path in paths:
        if not path.exists():
            results.append(CleanupResult(path, False, "not found"))
            continue
        if dry_run:
            results.append(CleanupResult(path, False, "would remove"))
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            results.append(CleanupResult(path, False, str(exc)))
            continue
        results.append(CleanupResult(path, True, "removed"))
    return tuple(results)


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
    if version < 3:
        # gui.port is back-filled from DEFAULT_SETTINGS by deep_merge; no data migration needed.
        migrated["config_version"] = 3
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
