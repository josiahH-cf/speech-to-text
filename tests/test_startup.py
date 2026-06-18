from pathlib import Path

from local_dictation.startup import (
    build_scheduled_task_xml,
    build_startup_command,
    disable_scheduled_task,
    enable_scheduled_task,
    scheduled_task_create_command,
    scheduled_task_delete_command,
    scheduled_task_query_command,
    startup_program_and_args,
    _split_command,
)


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


def test_startup_program_and_args_splits_program_and_arguments():
    program, arguments = startup_program_and_args("C:/Python312/pythonw.exe")

    assert program == "C:\\Python312\\pythonw.exe"
    assert arguments == "-m local_dictation run"


def test_split_command_handles_quoted_program():
    assert _split_command('"C:\\Apps\\LocalDictation.exe" run') == ("C:\\Apps\\LocalDictation.exe", "run")


def test_scheduled_task_xml_is_resilient_and_indefinite():
    xml = build_scheduled_task_xml("C:\\Apps\\LocalDictation.exe", "run", user="MACHINE\\me")

    assert '<Task version="1.2"' in xml
    assert "<LogonTrigger>" in xml
    assert "<UserId>MACHINE\\me</UserId>" in xml
    assert "<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>" in xml
    assert "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>" in xml
    assert "<RestartOnFailure>" in xml
    assert "<Count>3</Count>" in xml
    assert "<Command>C:\\Apps\\LocalDictation.exe</Command>" in xml
    assert "<Arguments>run</Arguments>" in xml


def test_scheduled_task_xml_escapes_and_omits_empty_arguments():
    xml = build_scheduled_task_xml("C:\\a & b\\App.exe", "", user="me")

    assert "<Command>C:\\a &amp; b\\App.exe</Command>" in xml
    assert "<Arguments>" not in xml


def test_scheduled_task_command_builders_use_task_name():
    assert scheduled_task_create_command("task.xml") == [
        "schtasks",
        "/Create",
        "/TN",
        "LocalDictation",
        "/XML",
        "task.xml",
        "/F",
    ]
    assert scheduled_task_delete_command() == ["schtasks", "/Delete", "/TN", "LocalDictation", "/F"]
    assert scheduled_task_query_command() == ["schtasks", "/Query", "/TN", "LocalDictation"]


def test_enable_scheduled_task_writes_xml_and_calls_schtasks(monkeypatch):
    captured = {}

    def fake_run(command):
        xml_path = command[command.index("/XML") + 1]
        captured["command"] = command
        captured["xml"] = Path(xml_path).read_text(encoding="utf-16")
        captured["existed_during_call"] = Path(xml_path).exists()
        return True, "SUCCESS"

    monkeypatch.setattr("local_dictation.startup._run_schtasks", fake_run)

    ok, message = enable_scheduled_task('"C:\\Apps\\LocalDictation.exe" run')

    assert ok is True
    assert message == "SUCCESS"
    assert captured["existed_during_call"] is True
    assert captured["command"][:4] == ["schtasks", "/Create", "/TN", "LocalDictation"]
    assert "<Command>C:\\Apps\\LocalDictation.exe</Command>" in captured["xml"]
    assert "<Arguments>run</Arguments>" in captured["xml"]


def test_disable_scheduled_task_when_absent(monkeypatch):
    monkeypatch.setattr("local_dictation.startup.scheduled_task_exists", lambda: False)

    ok, message = disable_scheduled_task()

    assert ok is True
    assert message == "not present"


def test_disable_scheduled_task_when_present(monkeypatch):
    monkeypatch.setattr("local_dictation.startup.scheduled_task_exists", lambda: True)
    captured = {}

    def fake_run(command):
        captured["command"] = command
        return True, "SUCCESS"

    monkeypatch.setattr("local_dictation.startup._run_schtasks", fake_run)

    ok, _message = disable_scheduled_task()

    assert ok is True
    assert captured["command"] == ["schtasks", "/Delete", "/TN", "LocalDictation", "/F"]
