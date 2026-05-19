import sys
from pathlib import Path

from local_dictation.commands import app_command, packaged_executable


def test_source_app_command_uses_module(monkeypatch):
    monkeypatch.delattr("sys.frozen", raising=False)
    monkeypatch.setattr(sys, "executable", "C:/Python312/python.exe")

    command = app_command("doctor")

    assert Path(command[0]) == Path("C:/Python312/python.exe")
    assert command[1:] == ["-m", "local_dictation", "doctor"]


def test_frozen_console_command_prefers_cli_sibling(monkeypatch, tmp_path):
    app = tmp_path / "LocalDictation.exe"
    cli = tmp_path / "LocalDictationCLI.exe"
    app.write_text("", encoding="utf-8")
    cli.write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(app))

    assert packaged_executable(console=True) == cli
    assert app_command("doctor", console=True) == [str(cli), "doctor"]


def test_frozen_window_command_prefers_windowed_sibling(monkeypatch, tmp_path):
    app = tmp_path / "LocalDictation.exe"
    cli = tmp_path / "LocalDictationCLI.exe"
    app.write_text("", encoding="utf-8")
    cli.write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(cli))

    assert packaged_executable(console=False) == app
    assert app_command("settings") == [str(app), "settings"]
