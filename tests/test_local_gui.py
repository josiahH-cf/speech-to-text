from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

from local_dictation.app import RuntimeControlResult
from local_dictation.config import load_settings
from local_dictation.local_gui import (
    LOCAL_GUI_HOST,
    LOCAL_GUI_PORT,
    LOCAL_GUI_URL,
    LocalGuiServer,
    _LocalGuiHTTPServer,
    _LocalGuiHandler,
)


class FakeApp:
    def __init__(self) -> None:
        self._runtime_enabled = True
        self.state = "IDLE"
        self.last_transcript = ""
        self.reload_forces: list[bool] = []
        self.hotkey_calls = 0

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
        self._runtime_enabled = True
        return RuntimeControlResult(True, "enabled")

    def disable_runtime(self) -> RuntimeControlResult:
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


def test_local_gui_uses_fixed_loopback_url():
    assert LOCAL_GUI_HOST == "127.0.0.1"
    assert LOCAL_GUI_PORT == 8765
    assert LOCAL_GUI_URL == "http://127.0.0.1:8765/"


def test_state_endpoint_returns_live_state_and_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    app.last_transcript = "hello"
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/state")

    assert status == 200
    assert body["runtimeEnabled"] is True
    assert body["state"] == "IDLE"
    assert body["hotkey"] == "ctrl+alt+space"
    assert body["sttModel"] == "base.en"
    assert body["insertionMode"] == "auto"
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
    assert saved["recording"]["input_device_id"] == 2
    assert saved["recording"]["gain_db"] == 6.0
    assert saved["recording"]["silence_stop"]["enabled"] is False
    assert saved["recording"]["silence_stop"]["silence_seconds"] == 2.2
    assert saved["recording"]["silence_stop"]["speech_threshold"] == 0.009
    assert app.reload_forces == [True]


def test_settings_endpoint_rejects_invalid_hotkey(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp()
    load_settings(create=True)

    with local_gui_test_server(app) as base_url:
        status, body = request_json(base_url, "/api/settings", {"hotkey": "ctrl+alt+nope"})

    assert status == 400
    assert "Unsupported hotkey" in body["error"]


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