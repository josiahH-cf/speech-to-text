from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .app import DictationApp
from .commands import app_command
from .config import logs_dir, settings_path
from .insertion import set_clipboard_text
from .logging_config import configure_logging


def _open_path(path: Path) -> None:
    os.startfile(str(path))  # type: ignore[attr-defined]


def _run_doctor() -> None:
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE
    subprocess.Popen(app_command("doctor", console=True), creationflags=creationflags)


def _icon_image():
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (64, 64), (28, 31, 35))
    draw = ImageDraw.Draw(image)
    draw.ellipse((14, 8, 50, 44), fill=(77, 163, 255))
    draw.rectangle((28, 40, 36, 52), fill=(77, 163, 255))
    draw.rectangle((20, 52, 44, 58), fill=(77, 163, 255))
    draw.ellipse((25, 15, 39, 36), fill=(28, 31, 35))
    return image


def run_tray(settings: dict) -> None:
    import pystray

    logger = configure_logging(settings)
    app = DictationApp(settings, logger=logger)
    app.start()

    def status_item(_item):
        return f"Status: {app.status_text()}"

    def toggle_recording(_icon, _item):
        app.handle_hotkey()

    def open_settings(_icon, _item):
        subprocess.Popen(app_command("settings"))

    def open_logs(_icon, _item):
        logs_dir().mkdir(parents=True, exist_ok=True)
        _open_path(logs_dir())

    def run_doctor(_icon, _item):
        _run_doctor()

    def copy_last_transcript(_icon, _item):
        if app.last_transcript:
            set_clipboard_text(app.last_transcript)

    def reload_settings(_icon, _item):
        app.reload_settings()

    def quit_app(icon, _item):
        app.stop()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(status_item, None, enabled=False),
        pystray.MenuItem("Start/Stop Recording", toggle_recording),
        pystray.MenuItem("Settings", open_settings),
        pystray.MenuItem("Reload Settings", reload_settings),
        pystray.MenuItem("Copy Last Transcript", copy_last_transcript, enabled=lambda _item: bool(app.last_transcript)),
        pystray.MenuItem("Open Logs", open_logs),
        pystray.MenuItem("Run Doctor", run_doctor),
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon("LocalDictation", _icon_image(), "Local Dictation", menu)

    try:
        icon.run()
    finally:
        app.stop()
