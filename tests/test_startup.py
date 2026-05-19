from local_dictation.startup import build_startup_command


def test_startup_command_uses_module_run():
    command = build_startup_command("C:/Python312/pythonw.exe")

    assert command == '"C:\\Python312\\pythonw.exe" -m local_dictation run'


def test_frozen_cli_startup_prefers_sibling_windowed_exe(monkeypatch, tmp_path):
    cli = tmp_path / "LocalDictationCLI.exe"
    app = tmp_path / "LocalDictation.exe"
    cli.write_text("", encoding="utf-8")
    app.write_text("", encoding="utf-8")

    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", str(cli))

    assert build_startup_command() == f'"{app}" run'
