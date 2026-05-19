import subprocess

from local_dictation.setup_manager import ollama_pull_command, run_command, winget_install_ollama_command


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
