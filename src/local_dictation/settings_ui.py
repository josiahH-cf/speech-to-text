from __future__ import annotations

import os
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

from .audio_cues import CUE_TONE_OPTIONS
from .commands import app_command
from .config import load_settings, logs_dir, save_settings, settings_path
from .settings_actions import update_settings as _updated_settings
from .startup import disable_startup, enable_startup, is_startup_enabled


def _bool(value) -> bool:
    return bool(value)


def _input_device_value(value) -> str:
    return "default" if value is None else str(value)


def _input_device_options() -> tuple[str, ...]:
    options = ["default"]
    try:
        import sounddevice as sd

        for index, device in enumerate(sd.query_devices()):
            if int(device.get("max_input_channels", 0)) > 0:
                options.append(f"{index}: {device.get('name', 'Input device')}")
    except Exception:
        pass
    return tuple(options)


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

        recording = self.settings.get("recording", {})
        self.input_device_id = tk.StringVar(value=_input_device_value(recording.get("input_device_id")))
        self.cue_tone = tk.StringVar(value=recording.get("cue_tone", "off"))
        self.gain_db = tk.StringVar(value=str(recording.get("gain_db", 0.0)))
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
        ttk.Label(frame, text="Input device").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, textvariable=self.input_device_id, values=_input_device_options(), width=29).grid(
            row=row, column=1, sticky="ew", pady=4
        )

        row += 1
        ttk.Label(frame, text="Recording cue").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, textvariable=self.cue_tone, values=CUE_TONE_OPTIONS, width=29).grid(
            row=row, column=1, sticky="ew", pady=4
        )

        row += 1
        ttk.Label(frame, text="Microphone gain dB").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.gain_db, width=32).grid(row=row, column=1, sticky="ew", pady=4)

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
        ttk.Button(button_frame, text="Open Settings Folder", command=self._open_settings_folder).grid(row=0, column=1, padx=4)
        ttk.Button(button_frame, text="Doctor", command=self._run_doctor).grid(row=0, column=2, padx=4)
        ttk.Button(button_frame, text="Save", command=self._save).grid(row=0, column=3, padx=4)
        ttk.Button(button_frame, text="Close", command=self.root.destroy).grid(row=0, column=4, padx=4)

    def _save(self) -> None:
        try:
            updated = _updated_settings(
                self.settings,
                hotkey=self.hotkey.get(),
                stt_model=self.stt_model.get(),
                cleanup_enabled=self.cleanup_enabled.get(),
                cleanup_model=self.cleanup_model.get(),
                insertion_mode=self.insertion_mode.get(),
                input_device_id=self.input_device_id.get(),
                cue_tone=self.cue_tone.get(),
                gain_db=self.gain_db.get(),
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

    def _open_settings_folder(self) -> None:
        settings_path().parent.mkdir(parents=True, exist_ok=True)
        os.startfile(str(settings_path().parent))  # type: ignore[attr-defined]

    def run(self) -> None:
        self.root.mainloop()


def run_settings_window() -> None:
    SettingsWindow().run()
