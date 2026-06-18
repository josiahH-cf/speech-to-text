from local_dictation.cli import main
from local_dictation.local_gui import LOCAL_GUI_URL


def test_gui_command_opens_existing_localhost_ui(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))

    result = main(["gui"])

    assert result == 0
    assert opened == [LOCAL_GUI_URL]
    assert LOCAL_GUI_URL in capsys.readouterr().out


def test_cleanup_data_requires_confirmation(capsys):
    result = main(["cleanup-data", "--app-data"])

    assert result == 2
    assert "--yes" in capsys.readouterr().out


def test_run_exits_when_another_instance_is_running(monkeypatch, capsys):
    started = []
    monkeypatch.setattr("local_dictation.cli.acquire_single_instance", lambda: False)
    monkeypatch.setattr("local_dictation.cli.load_settings", lambda *a, **k: started.append("loaded") or {})

    result = main(["run"])

    assert result == 0
    assert started == []
    assert "already running" in capsys.readouterr().out.lower()


def test_startup_status_reports_run_entry_and_scheduled_task(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr("local_dictation.cli.startup_command", lambda: '"X" run')
    monkeypatch.setattr("local_dictation.cli.scheduled_task_exists", lambda: True)

    result = main(["startup", "status"])

    assert result == 0
    out = capsys.readouterr().out
    assert "Run entry:" in out
    assert "Scheduled task: registered" in out


def test_cleanup_data_removes_app_data_and_model_cache(monkeypatch, tmp_path):
    app_data = tmp_path / "LocalDictation"
    model_cache = tmp_path / "models--Systran--faster-whisper-base.en"
    app_data.mkdir()
    model_cache.mkdir()

    monkeypatch.setattr("local_dictation.cli.app_data_dir", lambda: app_data)
    monkeypatch.setattr("local_dictation.cli.stt_model_cache_paths", lambda: (model_cache,))

    result = main(["cleanup-data", "--all", "--yes"])

    assert result == 0
    assert not app_data.exists()
    assert not model_cache.exists()