from local_dictation.cli import main
from local_dictation.local_gui import LOCAL_GUI_URL


def test_gui_command_opens_existing_localhost_ui(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))

    result = main(["gui"])

    assert result == 0
    assert opened == [LOCAL_GUI_URL]
    assert LOCAL_GUI_URL in capsys.readouterr().out