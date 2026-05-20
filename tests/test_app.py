from local_dictation.app import AppState, DictationApp
from local_dictation.config import default_settings


class FakeHotkeyListener:
    instances = []

    def __init__(self, hotkey, callback, *, logger=None):
        self.hotkey = hotkey
        self.callback = callback
        self.started = False
        self.stopped = False
        FakeHotkeyListener.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def is_listener_thread(self):
        return False


def patch_hotkeys(monkeypatch):
    FakeHotkeyListener.instances = []
    monkeypatch.setattr("local_dictation.app.GlobalHotkeyListener", FakeHotkeyListener)


def test_start_and_stop_are_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    patch_hotkeys(monkeypatch)
    app = DictationApp(default_settings())

    app.start()
    app.start()
    app.stop()
    app.stop()

    assert len(FakeHotkeyListener.instances) == 1
    assert FakeHotkeyListener.instances[0].started is True
    assert FakeHotkeyListener.instances[0].stopped is True
    assert app.runtime_enabled() is False


def test_runtime_disable_keeps_process_started_and_can_reenable(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    patch_hotkeys(monkeypatch)
    app = DictationApp(default_settings())

    app.start()
    disabled = app.disable_runtime()
    enabled = app.enable_runtime()
    app.stop()

    assert disabled.ok is True
    assert enabled.ok is True
    assert len(FakeHotkeyListener.instances) == 2
    assert FakeHotkeyListener.instances[0].stopped is True
    assert FakeHotkeyListener.instances[1].started is True


def test_runtime_disable_rejects_busy_recording_state(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    patch_hotkeys(monkeypatch)
    app = DictationApp(default_settings())
    app.start()

    app.state = AppState.RECORDING
    result = app.disable_runtime()
    app.stop()

    assert result.ok is False
    assert "RECORDING" in result.message
    assert FakeHotkeyListener.instances[0].stopped is True


def test_reload_settings_force_loads_even_when_mtime_is_unchanged(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = DictationApp(default_settings())
    app._settings_mtime = 1
    monkeypatch.setattr(app, "_current_settings_mtime", lambda: 1)
    calls = []

    def fake_load_settings(*, create=True):
        calls.append(create)
        settings = default_settings()
        settings["stt"]["model"] = "tiny.en"
        return settings

    monkeypatch.setattr("local_dictation.app.load_settings", fake_load_settings)

    app.reload_settings()
    assert calls == []

    app.reload_settings(force=True)
    assert calls == [True]
    assert app.settings["stt"]["model"] == "tiny.en"