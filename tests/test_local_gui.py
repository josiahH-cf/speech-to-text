from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

from local_dictation.app import RuntimeControlResult
from local_dictation.config import load_settings, save_settings
from local_dictation.local_gui import (
    LOCAL_GUI_HOST,
    LOCAL_GUI_PORT,
    LOCAL_GUI_URL,
    LocalGuiServer,
    _LocalGuiHTTPServer,
    _LocalGuiHandler,
    active_gui_url,
)


class FakeApp:
    def __init__(self) -> None:
        self._runtime_enabled = True
        self.state = "IDLE"
        self.last_transcript = ""
        self.reload_forces: list[bool] = []
        self.hotkey_calls = 0
        self.enable_calls = 0
        self.disable_calls = 0

    def runtime_enabled(self) -> bool:
        return self._runtime_enabled

    def status_text(self) -> str:
        return self.state

    def result_payload(self) -> dict[str, object]:
        return {
            "ok": False,
            "stage": "insertion",
            "message": "Could not restore target focus; final text is on the clipboard.",
            "inserted": False,
            "copiedToClipboard": True,
        }

    def reload_settings(self, *, force: bool = False) -> None:
        self.reload_forces.append(force)

    def enable_runtime(self) -> RuntimeControlResult:
        self.enable_calls += 1
        self._runtime_enabled = True
        return RuntimeControlResult(True, "enabled")

    def disable_runtime(self) -> RuntimeControlResult:
        self.disable_calls += 1
        if self.state != "IDLE":
            return RuntimeControlResult(False, "busy")
        self._runtime_enabled = False
        return RuntimeControlResult(True, "disabled")

    def handle_hotkey(self) -> None:
        self.hotkey_calls += 1
        self.state = "RECORDING" if self.state == "IDLE" else "IDLE"


@contextmanager
def local_gui_test_server(app: FakeApp):
    gui = LocalGuiServer(app)
    gui.token = "test-token"
    server = _LocalGuiHTTPServer((LOCAL_GUI_HOST, 0), _LocalGuiHandler, gui)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request_json(
    base_url: str,
    path: str,
    payload: dict | None = None,
    *,
    token: str | None = "test-token",
    origin: str | None = None,
):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["X-Local-Dictation-Token"] = token
    if origin is not None:
        headers["Origin"] = origin
    request = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def request_headers(base_url: str, path: str):
    request = urllib.request.Request(f"{base_url}{path}")
    with urllib.request.urlopen(request, timeout=5) as response:
        response.read()
        return response.status, response.headers


def request_text(base_url: str, path: str):
    request = urllib.request.Request(f"{base_url}{path}")
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, response.read().decode("utf-8")


def test_local_gui_default_constants():
    assert LOCAL_GUI_HOST == "127.0.0.1"
    assert LOCAL_GUI_PORT == 8765
    assert LOCAL_GUI_URL == "http://127.0.0.1:8765/"


def test_ping_endpoint_returns_app_identity():
    app = FakeApp()
    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/ping")
    assert status == 200
    assert body["app"] == "local-dictation"
    assert "version" in body


def test_local_gui_recovers_when_configured_port_is_busy(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    settings = load_settings(create=True)

    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind((LOCAL_GUI_HOST, 0))
    blocker.listen(1)
    occupied_port = blocker.getsockname()[1]
    settings["gui"]["port"] = occupied_port
    save_settings(settings)

    gui = LocalGuiServer(app)
    try:
        assert gui.start() is True
        assert gui.url != f"http://{LOCAL_GUI_HOST}:{occupied_port}/"
        assert active_gui_url() == gui.url
        status, body = request_json(gui.url, "/api/ping")
    finally:
        gui.stop()
        blocker.close()

    assert active_gui_url() is None
    assert status == 200
    assert body["app"] == "local-dictation"


def test_state_endpoint_returns_live_state_and_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    app.last_transcript = "hello"
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/state")

    assert status == 200
    assert body["runtimeEnabled"] is True
    assert body["editMode"] is False
    assert body["resumeRuntimeAfterEdit"] is False
    assert body["runtimePausedForEdit"] is False
    assert body["state"] == "IDLE"
    assert body["hotkey"] == "ctrl+alt+space"
    assert body["sttModel"] == "base.en"
    assert body["insertionMode"] == "auto"
    assert body["cueTone"] == "off"
    assert body["inputDeviceId"] == "default"
    assert body["gainDb"] == 0.0
    assert body["silenceEnabled"] is True
    assert body["silenceSeconds"] == 1.4
    assert body["speechThreshold"] == 0.012
    assert body["lastTranscriptAvailable"] is True
    assert body["lastResult"] == {
        "ok": False,
        "stage": "insertion",
        "message": "Could not restore target focus; final text is on the clipboard.",
        "inserted": False,
        "copiedToClipboard": True,
    }
    assert body["setup"] == {"ok": False, "steps": [{"name": "STT model", "ok": False, "message": "base.en"}]}


def test_local_gui_security_headers_are_present(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        html_status, html_headers = request_headers(base_url, "/")
        json_status, json_headers = request_headers(base_url, "/api/state")

    assert html_status == 200
    assert json_status == 200
    assert html_headers["X-Content-Type-Options"] == "nosniff"
    assert json_headers["X-Content-Type-Options"] == "nosniff"
    assert html_headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in html_headers["Content-Security-Policy"]


def test_setup_endpoint_returns_core_speech_model_status(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    settings = load_settings(create=True)
    settings["setup"]["stt_model_ready"] = True
    settings["stt"]["model"] = "small.en"
    from local_dictation.config import save_settings

    save_settings(settings)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/setup")

    assert status == 200
    assert body == {"ok": True, "steps": [{"name": "STT model", "ok": True, "message": "small.en"}]}


def test_settings_endpoint_saves_and_forces_reload(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(
            base_url,
            "/api/settings",
            {
                "hotkey": "Ctrl-Alt-Space",
                "sttModel": "tiny.en",
                "cleanupEnabled": True,
                "cleanupModel": "llama3.2:1b",
                "insertionMode": "clipboard",
                "cueTone": "soft_ding",
                "inputDeviceId": "2: USB Mic",
                "gainDb": "6",
                "silenceEnabled": False,
                "silenceSeconds": "2.2",
                "speechThreshold": "0.009",
            },
        )

    saved = load_settings(create=True)
    assert status == 200
    assert body["sttModel"] == "tiny.en"
    assert saved["hotkey"] == "ctrl+alt+space"
    assert saved["cleanup"]["enabled"] is True
    assert saved["cleanup"]["model"] == "llama3.2:1b"
    assert saved["insertion"]["mode"] == "clipboard"
    assert saved["recording"]["cue_tone"] == "soft_ding"
    assert saved["recording"]["input_device_id"] == 2
    assert saved["recording"]["gain_db"] == 6.0
    assert saved["recording"]["silence_stop"]["enabled"] is False
    assert saved["recording"]["silence_stop"]["silence_seconds"] == 2.2
    assert saved["recording"]["silence_stop"]["speech_threshold"] == 0.009
    assert app.reload_forces == [True]


def test_edit_mode_endpoint_pauses_runtime_and_tracks_resume(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/edit-mode", {"enabled": True})

    assert status == 200
    assert body["editMode"] is True
    assert body["runtimeEnabled"] is False
    assert body["resumeRuntimeAfterEdit"] is True
    assert body["runtimePausedForEdit"] is True
    assert app.disable_calls == 1
    assert app.enable_calls == 0


def test_edit_mode_endpoint_rejects_busy_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    app.state = "RECORDING"
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/edit-mode", {"enabled": True})
        state_status, state_body = request_json(base_url, "/api/state")

    assert status == 409
    assert body["error"] == "Dictation runtime is busy: RECORDING."
    assert state_status == 200
    assert state_body["editMode"] is False
    assert app.runtime_enabled() is True
    assert app.disable_calls == 0
    assert app.enable_calls == 0


def test_edit_mode_cancel_resumes_only_when_it_paused_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        enter_status, enter_body = request_json(base_url, "/api/edit-mode", {"enabled": True})
        exit_status, exit_body = request_json(base_url, "/api/edit-mode", {"enabled": False})

    assert enter_status == 200
    assert enter_body["editMode"] is True
    assert exit_status == 200
    assert exit_body["editMode"] is False
    assert exit_body["runtimeEnabled"] is True
    assert app.disable_calls == 1
    assert app.enable_calls == 1


def test_edit_mode_cancel_keeps_previously_disabled_runtime_off(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    app._runtime_enabled = False
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        enter_status, enter_body = request_json(base_url, "/api/edit-mode", {"enabled": True})
        exit_status, exit_body = request_json(base_url, "/api/edit-mode", {"enabled": False})

    assert enter_status == 200
    assert enter_body["editMode"] is True
    assert enter_body["resumeRuntimeAfterEdit"] is False
    assert exit_status == 200
    assert exit_body["editMode"] is False
    assert exit_body["runtimeEnabled"] is False
    assert app.disable_calls == 0
    assert app.enable_calls == 0


def test_settings_endpoint_in_edit_mode_saves_reloads_and_resumes(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        enter_status, enter_body = request_json(base_url, "/api/edit-mode", {"enabled": True})
        save_status, save_body = request_json(
            base_url,
            "/api/settings",
            {
                "hotkey": "Ctrl-Alt-Space",
                "sttModel": "tiny.en",
                "cleanupEnabled": True,
                "cleanupModel": "llama3.2:1b",
                "insertionMode": "clipboard",
                "inputDeviceId": "default",
                "gainDb": "3",
                "silenceEnabled": True,
                "silenceSeconds": "1.8",
                "speechThreshold": "0.011",
            },
        )

    saved = load_settings(create=True)
    assert enter_status == 200
    assert enter_body["editMode"] is True
    assert save_status == 200
    assert save_body["editMode"] is False
    assert save_body["runtimeEnabled"] is True
    assert save_body["sttModel"] == "tiny.en"
    assert saved["stt"]["model"] == "tiny.en"
    assert saved["recording"]["gain_db"] == 3.0
    assert app.disable_calls == 1
    assert app.enable_calls == 1
    assert app.reload_forces == [True]


def test_invalid_settings_save_keeps_edit_mode_active(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        enter_status, enter_body = request_json(base_url, "/api/edit-mode", {"enabled": True})
        save_status, save_body = request_json(base_url, "/api/settings", {"hotkey": "ctrl+alt+nope"})
        state_status, state_body = request_json(base_url, "/api/state")

    assert enter_status == 200
    assert enter_body["editMode"] is True
    assert save_status == 400
    assert "Unsupported hotkey" in save_body["error"]
    assert state_status == 200
    assert state_body["editMode"] is True
    assert state_body["runtimeEnabled"] is False
    assert app.disable_calls == 1
    assert app.enable_calls == 0
    assert app.reload_forces == []


def test_settings_endpoint_rejects_invalid_hotkey(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/settings", {"hotkey": "ctrl+alt+nope"})

    assert status == 400
    assert "Unsupported hotkey" in body["error"]


def test_settings_endpoint_rejects_invalid_recording_cue(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/settings", {"cueTone": "loud_bell"})

    assert status == 400
    assert "Recording cue" in body["error"]


def test_browser_page_wires_edit_mode_and_skips_refresh_while_editing(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, html = request_text(base_url, "/")

    assert status == 200
    assert 'id="edit-mode-button"' in html
    assert 'id="cancel-edit-button"' in html
    assert 'id="cue-tone"' in html
    assert 'value="soft_ding"' in html
    assert 'value="low_chime"' in html
    assert 'value="muted_tick"' in html
    assert 'cueTone: $("cue-tone").value' in html
    assert 'post("/api/edit-mode", { enabled: true })' in html
    assert 'post("/api/edit-mode", { enabled: false })' in html
    assert 'const preserveSettings = options.preserveSettings ?? state?.editMode === true;' in html
    assert 'if (!preserveSettings) renderSettings(state);' in html
    assert 'if (state?.editMode !== true) refresh().catch' in html


def test_runtime_endpoint_returns_busy_when_app_is_not_idle(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    app.state = "RECORDING"
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/runtime", {"enabled": False})

    assert status == 409
    assert body["error"] == "busy"
    assert app.runtime_enabled() is True


def test_mutation_requires_token(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/runtime", {"enabled": False}, token=None)

    assert status == 403
    assert "token" in body["error"].lower()


def test_mutation_accepts_local_origin(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/runtime", {"enabled": False}, origin=base_url)

    assert status == 200
    assert body["runtimeEnabled"] is False


def test_mutation_rejects_foreign_origin(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/runtime", {"enabled": False}, origin="https://example.com")

    assert status == 403
    assert "origin" in body["error"].lower()
    assert app.runtime_enabled() is True


def test_recording_endpoint_uses_existing_hotkey_flow(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/recording", {})

    assert status == 200
    assert body["state"] == "RECORDING"
    assert app.hotkey_calls == 1