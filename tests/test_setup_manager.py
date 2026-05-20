import subprocess

from local_dictation.setup_manager import (
    bootstrap_setup,
    collect_setup_status,
    ollama_pull_command,
    run_command,
    winget_install_ollama_command,
)


def test_winget_ollama_install_command_is_silent_and_exact():
    command = winget_install_ollama_command()

    assert command[:4] == ["winget", "install", "--id", "Ollama.Ollama"]
    assert "--exact" in command
    assert "--silent" in command


def test_ollama_pull_command_uses_configured_model():
    assert ollama_pull_command("gemma3:1b") == ["ollama", "pull", "gemma3:1b"]


def test_run_command_decodes_output_with_replacement(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    ok, message = run_command(["not-a-real-command"])

    assert ok is True
    assert message == "ok"
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"


def test_bootstrap_can_prepare_stt_without_ollama(monkeypatch, tmp_path):
    settings = {
        "stt": {"model": "base.en"},
        "cleanup": {"model": "gemma3:1b"},
        "setup": {"ollama_install": "auto"},
    }

    class FakeTranscriber:
        def __init__(self, stt_settings, *, logger=None):
            assert stt_settings["model"] == "base.en"

        def download_model(self):
            return None

    monkeypatch.setattr("local_dictation.setup_manager.FasterWhisperTranscriber", FakeTranscriber)
    monkeypatch.setattr("local_dictation.setup_manager.command_available", lambda command: False)
    monkeypatch.setattr("local_dictation.setup_manager.save_settings", lambda saved_settings: tmp_path / "settings.json")

    status = bootstrap_setup(settings, include_ollama=False)

    assert status.ok is True
    assert [step.name for step in status.steps] == ["STT model"]
    assert settings["setup"]["stt_model_ready"] is True
    assert "ollama_ready" not in settings["setup"]


def test_bootstrap_can_prepare_ollama_without_stt(monkeypatch, tmp_path):
    settings = {
        "stt": {"model": "base.en"},
        "cleanup": {"model": "gemma3:1b"},
        "setup": {"ollama_install": "auto", "stt_model_ready": False},
    }

    def fake_command_available(command):
        return command == "ollama"

    monkeypatch.setattr("local_dictation.setup_manager.command_available", fake_command_available)
    monkeypatch.setattr("local_dictation.setup_manager.run_command", lambda command: (True, "pulled"))
    monkeypatch.setattr("local_dictation.setup_manager.save_settings", lambda saved_settings: tmp_path / "settings.json")

    status = bootstrap_setup(settings, include_stt=False)

    assert status.ok is True
    assert [step.name for step in status.steps] == ["Install Ollama", "Ollama model"]
    assert settings["setup"]["stt_model_ready"] is False
    assert settings["setup"]["ollama_ready"] is True


def test_setup_status_defaults_to_core_stt_status(monkeypatch):
    settings = {
        "stt": {"model": "base.en"},
        "cleanup": {"enabled": False},
        "setup": {"stt_model_ready": True, "ollama_install": "auto"},
    }

    monkeypatch.setattr("local_dictation.setup_manager.command_available", lambda command: False)

    status = collect_setup_status(settings)

    assert status.ok is True
    assert [step.name for step in status.steps] == ["STT model"]


def test_setup_status_can_include_optional_ollama_checks(monkeypatch):
    settings = {
        "stt": {"model": "base.en"},
        "cleanup": {"enabled": False, "endpoint": "http://localhost:11434/api/generate"},
        "setup": {"stt_model_ready": True, "ollama_install": "auto"},
    }

    monkeypatch.setattr("local_dictation.setup_manager.command_available", lambda command: False)
    monkeypatch.setattr("local_dictation.setup_manager.check_ollama", lambda endpoint, timeout_seconds=2: (False, "offline"))

    status = collect_setup_status(settings, include_ollama=True)

    assert status.ok is False
    assert [step.name for step in status.steps] == ["STT model", "winget", "Ollama executable", "Ollama API"]
