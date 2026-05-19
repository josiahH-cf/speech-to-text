from __future__ import annotations

import copy
import os
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from .commands import app_command
from .config import load_settings, logs_dir, save_settings
from .hotkey import parse_hotkey
from .startup import disable_startup, enable_startup, is_startup_enabled

VALID_INSERTION_MODES = {"auto", "direct", "typing", "clipboard"}


def _bool(value) -> bool:
    return bool(value)


def _required_text(value: str, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text


def _positive_float(value: str, field_name: str) -> float:
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


def _updated_settings(
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
    updated = copy.deepcopy(settings)
    normalized_hotkey = parse_hotkey(_required_text(hotkey, "Hotkey")).normalized
    model = _required_text(stt_model, "Speech model")
    cleanup_model_name = _required_text(cleanup_model, "Ollama model")
    normalized_insertion_mode = _required_text(insertion_mode, "Insertion mode").lower()
    if normalized_insertion_mode not in VALID_INSERTION_MODES:
        raise ValueError("Insertion mode must be auto, direct, typing, or clipboard.")

    updated["hotkey"] = normalized_hotkey
    updated.setdefault("stt", {})["model"] = model
    updated.setdefault("cleanup", {})["enabled"] = cleanup_enabled
    updated.setdefault("cleanup", {})["model"] = cleanup_model_name
    updated.setdefault("insertion", {})["mode"] = normalized_insertion_mode

    silence = updated.setdefault("recording", {}).setdefault("silence_stop", {})
    silence["enabled"] = silence_enabled
    silence["silence_seconds"] = _positive_float(silence_seconds, "Silence seconds")
    silence["speech_threshold"] = _positive_float(speech_threshold, "Speech threshold")
    updated.setdefault("startup", {})["enabled"] = startup_enabled
    return updated


class SettingsWindow:
    def __init__(self) -> None:
        self.settings = load_settings(create=True)
        self.root = tk.Tk()
        self.root.title("Local Dictation Settings")
        self.root.resizable(False, False)

        self.hotkey = tk.StringVar(value=self.settings.get("hotkey", "ctrl+alt+space"))
        self.stt_model = tk.StringVar(value=self.settings.get("stt", {}).get("model", "base.en"))
        self.cleanup_enabled = tk.BooleanVar(value=_bool(self.settings.get("cleanup", {}).get("enabled", False)))
        self.cleanup_model = tk.StringVar(value=self.settings.get("cleanup", {}).get("model", "gemma3:1b"))
        self.insertion_mode = tk.StringVar(value=self.settings.get("insertion", {}).get("mode", "auto"))
        self.startup_enabled = tk.BooleanVar(value=is_startup_enabled())

        silence = self.settings.get("recording", {}).get("silence_stop", {})
        self.silence_enabled = tk.BooleanVar(value=_bool(silence.get("enabled", True)))
        self.speech_threshold = tk.StringVar(value=str(silence.get("speech_threshold", 0.012)))
        self.silence_seconds = tk.StringVar(value=str(silence.get("silence_seconds", 1.4)))

        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")

        row = 0
        ttk.Label(frame, text="Hotkey").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.hotkey, width=32).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Speech model").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, textvariable=self.stt_model, values=("tiny.en", "base.en", "small.en", "medium.en"), width=29).grid(
            row=row, column=1, sticky="ew", pady=4
        )

        row += 1
        ttk.Label(frame, text="Insertion").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, textvariable=self.insertion_mode, values=("auto", "direct", "clipboard"), width=29).grid(
            row=row, column=1, sticky="ew", pady=4
        )

        row += 1
        ttk.Checkbutton(frame, text="Stop after silence", variable=self.silence_enabled).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=4
        )

        row += 1
        ttk.Label(frame, text="Silence seconds").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.silence_seconds, width=32).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Label(frame, text="Speech threshold").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.speech_threshold, width=32).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Checkbutton(frame, text="Use Ollama cleanup", variable=self.cleanup_enabled).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=4
        )

        row += 1
        ttk.Label(frame, text="Ollama model").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.cleanup_model, width=32).grid(row=row, column=1, sticky="ew", pady=4)

        row += 1
        ttk.Checkbutton(frame, text="Start on login", variable=self.startup_enabled).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=4
        )

        row += 1
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(button_frame, text="Open Logs", command=self._open_logs).grid(row=0, column=0, padx=4)
        ttk.Button(button_frame, text="Doctor", command=self._run_doctor).grid(row=0, column=1, padx=4)
        ttk.Button(button_frame, text="Save", command=self._save).grid(row=0, column=2, padx=4)
        ttk.Button(button_frame, text="Close", command=self.root.destroy).grid(row=0, column=3, padx=4)

    def _save(self) -> None:
        try:
            updated = _updated_settings(
                self.settings,
                hotkey=self.hotkey.get(),
                stt_model=self.stt_model.get(),
                cleanup_enabled=self.cleanup_enabled.get(),
                cleanup_model=self.cleanup_model.get(),
                insertion_mode=self.insertion_mode.get(),
                silence_enabled=self.silence_enabled.get(),
                silence_seconds=self.silence_seconds.get(),
                speech_threshold=self.speech_threshold.get(),
                startup_enabled=self.startup_enabled.get(),
            )

            if self.startup_enabled.get():
                enable_startup()
            else:
                disable_startup()

            self.settings = updated
            save_settings(self.settings)
        except Exception as exc:
            messagebox.showerror("Local Dictation", f"Settings were not saved:\n{exc}")
            return
        messagebox.showinfo("Local Dictation", "Settings saved.")

    def _run_doctor(self) -> None:
        creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
        subprocess.Popen(app_command("doctor", console=True), creationflags=creationflags)

    def _open_logs(self) -> None:
        logs_dir().mkdir(parents=True, exist_ok=True)
        os.startfile(str(logs_dir()))  # type: ignore[attr-defined]

    def run(self) -> None:
        self.root.mainloop()


def run_settings_window() -> None:
    SettingsWindow().run()
