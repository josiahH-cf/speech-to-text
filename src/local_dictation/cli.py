from __future__ import annotations

import argparse
import time
import wave

from .config import load_settings, save_settings
from .doctor import run_doctor
from .insertion import insert_text
from .logging_config import configure_logging
from .recorder import RecordingResult
from .setup_manager import bootstrap_setup, collect_setup_status
from .startup import build_startup_command, disable_startup, enable_startup, startup_command
from .transcriber import FasterWhisperTranscriber


def _run(args: argparse.Namespace) -> int:
    settings = load_settings(create=True)
    if args.no_tray:
        from .app import DictationApp

        logger = configure_logging(settings, console=True)
        app = DictationApp(settings, logger=logger)
        app.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            app.stop()
        return 0

    from .tray import run_tray

    run_tray(settings)
    return 0


def _download_model(_args: argparse.Namespace) -> int:
    settings = load_settings(create=True)
    logger = configure_logging(settings, console=True)
    transcriber = FasterWhisperTranscriber(settings.get("stt", {}), logger=logger)
    transcriber.download_model()
    settings.setdefault("setup", {})["stt_model_ready"] = True
    save_settings(settings)
    print(f"Model is ready: {settings.get('stt', {}).get('model', 'base.en')}")
    return 0


def _startup(args: argparse.Namespace) -> int:
    settings = load_settings(create=True)
    if args.action == "enable":
        command = build_startup_command()
        enable_startup(command)
        settings.setdefault("startup", {})["enabled"] = True
        save_settings(settings)
        print(f"Startup enabled: {command}")
        return 0
    if args.action == "disable":
        disable_startup()
        settings.setdefault("startup", {})["enabled"] = False
        save_settings(settings)
        print("Startup disabled.")
        return 0
    command = startup_command()
    print(command or "Startup is not enabled.")
    return 0


def _setup(args: argparse.Namespace) -> int:
    settings = load_settings(create=True)
    logger = configure_logging(settings, console=True)
    if args.action == "bootstrap":
        include_stt = not getattr(args, "ollama_only", False)
        include_ollama = not getattr(args, "stt_only", False)
        if not include_stt and not include_ollama:
            print("Choose either --stt-only or --ollama-only, not both.")
            return 2
        status = bootstrap_setup(settings, logger=logger, include_stt=include_stt, include_ollama=include_ollama)
    else:
        include_stt = not getattr(args, "ollama_only", False)
        include_ollama = bool(getattr(args, "with_ollama", False) or getattr(args, "ollama_only", False))
        status = collect_setup_status(settings, include_stt=include_stt, include_ollama=include_ollama)
    print(status.render())
    return 0 if status.ok else 1


def _settings(_args: argparse.Namespace) -> int:
    from .settings_ui import run_settings_window

    run_settings_window()
    return 0


def _gui(_args: argparse.Namespace) -> int:
    import webbrowser

    from .local_gui import LOCAL_GUI_URL

    webbrowser.open(LOCAL_GUI_URL)
    print(f"Opened {LOCAL_GUI_URL}")
    return 0


def _read_wav(path: str) -> RecordingResult:
    import numpy as np

    with wave.open(path, "rb") as handle:
        channels = handle.getnchannels()
        sample_rate = handle.getframerate()
        sample_width = handle.getsampwidth()
        frames = handle.readframes(handle.getnframes())
        duration = handle.getnframes() / sample_rate if sample_rate else 0.0

    if sample_width == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype("float32") / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype("float32") / 2147483648.0
    else:
        raise ValueError("Only 16-bit or 32-bit PCM WAV files are supported.")
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return RecordingResult(audio=audio, sample_rate=sample_rate, duration_seconds=duration)


def _transcribe_file(args: argparse.Namespace) -> int:
    settings = load_settings(create=True)
    logger = configure_logging(settings, console=True)
    recording = _read_wav(args.wav)
    result = FasterWhisperTranscriber(settings.get("stt", {}), logger=logger).transcribe(recording)
    print(result.text)
    return 0


def _insert_test(args: argparse.Namespace) -> int:
    from .insertion import capture_foreground_window

    settings = load_settings(create=True)
    logger = configure_logging(settings, console=True)
    result = insert_text(args.text, capture_foreground_window(), settings.get("insertion", {}), logger=logger)
    print(result.message)
    return 0 if result.inserted else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-dictation")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the resident dictation app.")
    run_parser.add_argument("--no-tray", action="store_true", help="Run without tray icon for console debugging.")
    run_parser.set_defaults(func=_run)

    doctor_parser = subparsers.add_parser("doctor", help="Check local setup.")
    doctor_parser.set_defaults(func=lambda _args: run_doctor())

    download_parser = subparsers.add_parser("download-model", help="Download or prepare the configured STT model.")
    download_parser.set_defaults(func=_download_model)

    startup_parser = subparsers.add_parser("startup", help="Manage Windows login startup.")
    startup_parser.add_argument("action", choices=["enable", "disable", "status"])
    startup_parser.set_defaults(func=_startup)

    setup_parser = subparsers.add_parser("setup", help="Run or inspect first-run setup.")
    setup_parser.add_argument("action", choices=["bootstrap", "status"])
    setup_parser.add_argument("--stt-only", action="store_true", help="Prepare only the local speech-to-text model.")
    setup_parser.add_argument("--ollama-only", action="store_true", help="Prepare only the optional Ollama cleanup layer.")
    setup_parser.add_argument("--with-ollama", action="store_true", help="Include optional Ollama cleanup checks in setup status.")
    setup_parser.set_defaults(func=_setup)

    settings_parser = subparsers.add_parser("settings", help="Open the settings window.")
    settings_parser.set_defaults(func=_settings)

    gui_parser = subparsers.add_parser("gui", help="Open the local browser UI.")
    gui_parser.set_defaults(func=_gui)

    transcribe_parser = subparsers.add_parser("transcribe-file", help="Transcribe a local WAV file.")
    transcribe_parser.add_argument("wav")
    transcribe_parser.set_defaults(func=_transcribe_file)

    insert_parser = subparsers.add_parser("insert-test", help="Insert test text into the current foreground window.")
    insert_parser.add_argument("--text", required=True)
    insert_parser.set_defaults(func=_insert_test)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return int(args.func(args))
