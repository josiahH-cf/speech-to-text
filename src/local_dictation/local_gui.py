from __future__ import annotations

import json
import logging
import os
import secrets
import socket
import threading
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import app_data_dir, load_settings, save_settings, settings_path
from . import __version__
from .settings_actions import update_settings
from .setup_manager import collect_setup_status

LOCAL_GUI_HOST = "127.0.0.1"
LOCAL_GUI_PORT = 8765
LOCAL_GUI_URL = f"http://{LOCAL_GUI_HOST}:{LOCAL_GUI_PORT}/"
LOCAL_GUI_FALLBACK_PORT_COUNT = 20
LOCAL_GUI_STATE_FILENAME = "local-gui.json"
MAX_JSON_BYTES = 16 * 1024
LOCAL_GUI_ALLOWED_HOSTS = {LOCAL_GUI_HOST, "localhost"}
SECURITY_HEADERS = (
  ("X-Content-Type-Options", "nosniff"),
  ("Referrer-Policy", "no-referrer"),
  (
    "Content-Security-Policy",
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'",
  ),
)


@dataclass(frozen=True)
class _ControlResult:
  ok: bool
  message: str


def active_gui_state_path() -> Path:
    return app_data_dir() / LOCAL_GUI_STATE_FILENAME


def _valid_port(value: Any, default: int = LOCAL_GUI_PORT) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return default
    if port < 0 or port > 65535:
        return default
    return port


def configured_gui_port(settings: dict[str, Any] | None = None) -> int:
    source = settings if settings is not None else load_settings(create=False)
    return _valid_port(source.get("gui", {}).get("port", LOCAL_GUI_PORT))


def configured_gui_url(settings: dict[str, Any] | None = None) -> str:
    return f"http://{LOCAL_GUI_HOST}:{configured_gui_port(settings)}/"


def _candidate_ports(preferred_port: int) -> tuple[int, ...]:
    if preferred_port == 0:
        return (0,)
    last_port = min(65535, preferred_port + LOCAL_GUI_FALLBACK_PORT_COUNT)
    return tuple(range(preferred_port, last_port + 1))


def _loopback_port_accepts_connections(port: int) -> bool:
    try:
        with socket.create_connection((LOCAL_GUI_HOST, port), timeout=0.2):
            return True
    except OSError:
        return False


def _read_active_gui_state() -> dict[str, Any] | None:
    try:
        loaded = json.loads(active_gui_state_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def active_gui_url() -> str | None:
    state = _read_active_gui_state()
    if not state:
        return None
    url = state.get("url")
    if not isinstance(url, str):
        return None
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in LOCAL_GUI_ALLOWED_HOSTS:
        return None
    return url if url.endswith("/") else f"{url}/"


def candidate_gui_urls() -> tuple[str, ...]:
    urls: list[str] = []
    active_url = active_gui_url()
    if active_url:
        urls.append(active_url)
    configured_url = configured_gui_url()
    if configured_url not in urls:
        urls.append(configured_url)
    return tuple(urls)


class LocalGuiServer:
    def __init__(self, app, *, logger: logging.Logger | None = None) -> None:
        self.app = app
        self.logger = logger or logging.getLogger(__name__)
        self.token = secrets.token_urlsafe(24)
        self._server: _LocalGuiHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port: int = LOCAL_GUI_PORT
        self._edit_lock = threading.RLock()
        self._edit_mode = False
        self._resume_runtime_after_edit = False

    @property
    def url(self) -> str:
        return f"http://{LOCAL_GUI_HOST}:{self._port}/"

    def start(self) -> bool:
        if self._server is not None:
            return True
        preferred_port = configured_gui_port()
        errors: list[tuple[int, OSError]] = []
        server = None
        for port in _candidate_ports(preferred_port):
            if port != 0 and _loopback_port_accepts_connections(port):
                exc = OSError(f"port {port} is already accepting loopback connections")
                errors.append((port, exc))
                if port == preferred_port:
                    self.logger.warning("Localhost GUI could not bind http://%s:%s/: %s", LOCAL_GUI_HOST, port, exc)
                else:
                    self.logger.debug("Localhost GUI fallback port %s was unavailable: %s", port, exc)
                continue
            try:
                server = _LocalGuiHTTPServer((LOCAL_GUI_HOST, port), _LocalGuiHandler, self)
                break
            except OSError as exc:
                errors.append((port, exc))
                if port == preferred_port:
                    self.logger.warning("Localhost GUI could not bind http://%s:%s/: %s", LOCAL_GUI_HOST, port, exc)
                else:
                    self.logger.debug("Localhost GUI fallback port %s was unavailable: %s", port, exc)
        if server is None:
            attempted = ", ".join(str(port) for port, _exc in errors)
            last_error = errors[-1][1] if errors else "no ports attempted"
            self.logger.warning("Localhost GUI could not bind any loopback port (%s): %s", attempted, last_error)
            return False
        self._port = server.server_address[1]
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, name="localhost-gui", daemon=True)
        self._thread.start()
        self._write_active_state()
        if self._port != preferred_port:
            self.logger.warning("Localhost GUI recovered on %s after port %s was unavailable.", self.url, preferred_port)
        else:
            self.logger.info("Localhost GUI listening at %s", self.url)
        return True

    def stop(self) -> None:
        server = self._server
        if server is None:
            return
        self._server = None
        server.shutdown()
        server.server_close()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self._clear_active_state()
        self.logger.info("Localhost GUI stopped.")

    def open_browser(self) -> None:
        webbrowser.open(self.url)

    def edit_state(self) -> dict[str, bool]:
      with self._edit_lock:
        return {
          "editMode": self._edit_mode,
          "resumeRuntimeAfterEdit": self._resume_runtime_after_edit,
          "runtimePausedForEdit": self._edit_mode and self._resume_runtime_after_edit,
        }

    def enter_edit_mode(self):
      with self._edit_lock:
        if self._edit_mode:
          return _ControlResult(True, "Edit mode is already active.")
        status = self.app.status_text()
        if status != "IDLE":
          return _ControlResult(False, f"Dictation runtime is busy: {status}.")
        resume_runtime = bool(self.app.runtime_enabled())
        if resume_runtime:
          result = self.app.disable_runtime()
          if not result.ok:
            return result
        self._edit_mode = True
        self._resume_runtime_after_edit = resume_runtime
        return _ControlResult(True, "Edit mode enabled.")

    def exit_edit_mode(self):
      with self._edit_lock:
        if not self._edit_mode:
          return _ControlResult(True, "Edit mode is not active.")
        resume_runtime = self._resume_runtime_after_edit
        if not resume_runtime:
          self._edit_mode = False
          self._resume_runtime_after_edit = False
          return _ControlResult(True, "Edit mode closed.")
        result = self.app.enable_runtime()
        if not result.ok:
          return result
        self._edit_mode = False
        self._resume_runtime_after_edit = False
        return _ControlResult(True, "Settings saved and runtime resumed.")

    def _write_active_state(self) -> None:
        payload = {
            "app": "local-dictation",
            "version": __version__,
            "pid": os.getpid(),
            "host": LOCAL_GUI_HOST,
            "port": self._port,
            "url": self.url,
            "updated_at": time.time(),
        }
        try:
            path = active_gui_state_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            self.logger.warning("Could not write localhost GUI state: %s", exc)

    def _clear_active_state(self) -> None:
        path = active_gui_state_path()
        try:
            state = _read_active_gui_state()
            if state and state.get("pid") not in {None, os.getpid()}:
                return
            path.unlink(missing_ok=True)
        except OSError as exc:
            self.logger.debug("Could not remove localhost GUI state: %s", exc)


class _LocalGuiHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, server_address, handler_class, gui: LocalGuiServer) -> None:
        super().__init__(server_address, handler_class)
        self.gui = gui


class _LocalGuiHandler(BaseHTTPRequestHandler):
    server: _LocalGuiHTTPServer

    def log_message(self, format: str, *args) -> None:
        self.server.gui.logger.debug("Localhost GUI: " + format, *args)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(_page_html(self.server.gui.token, self.server.gui.url))
            return
        if path == "/api/state":
            self._send_json(self._state_payload())
            return
        if path == "/api/setup":
            self._send_json(self._setup_payload())
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if path == "/api/ping":
            self._send_json({"app": "local-dictation", "version": __version__})
            return
        self._send_error(404, "Not found.")

    def do_POST(self) -> None:
      if self.headers.get("X-Local-Dictation-Token") != self.server.gui.token:
        self._send_error(403, "Invalid local GUI token.")
        return
      if not self._request_origin_is_allowed():
        self._send_error(403, "Invalid local GUI origin.")
        return

      path = urlparse(self.path).path
      try:
        payload = self._read_json()
        if path == "/api/settings":
          self._update_settings(payload)
          self._send_json(self._state_payload())
          return
        if path == "/api/edit-mode":
          self._update_edit_mode(payload)
          return
        if path == "/api/runtime":
          self._update_runtime(payload)
          return
        if path == "/api/recording":
          self._toggle_recording()
          return
      except ValueError as exc:
        self._send_error(400, str(exc))
        return
      except BusyError as exc:
        self._send_error(409, str(exc))
        return
      except Exception as exc:
        self.server.gui.logger.exception("Localhost GUI request failed.")
        self._send_error(500, f"Request failed: {exc}")
        return

      self._send_error(404, "Not found.")

    def _read_json(self) -> dict[str, Any]:
        length_text = self.headers.get("Content-Length", "0")
        try:
            length = int(length_text)
        except ValueError:
            raise ValueError("Invalid Content-Length.") from None
        if length > MAX_JSON_BYTES:
            raise ValueError("Request body is too large.")
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _request_origin_is_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urlparse(origin)
        if parsed.scheme.lower() != "http":
            return False
        hostname = (parsed.hostname or "").lower()
        if hostname not in LOCAL_GUI_ALLOWED_HOSTS:
            return False
        try:
            port = parsed.port
        except ValueError:
            return False
        return port == int(self.server.server_address[1])

    def _state_payload(self) -> dict[str, Any]:
        app = self.server.gui.app
        settings = load_settings(create=True)
        insertion = settings.get("insertion", {})
        recording = settings.get("recording", {})
        silence = recording.get("silence_stop", {})
        result_payload = (
            app.result_payload()
            if hasattr(app, "result_payload")
            else {"ok": True, "stage": "idle", "message": "Dictation is ready.", "inserted": False, "copiedToClipboard": False}
        )
        return {
            "running": True,
            "runtimeEnabled": app.runtime_enabled(),
          **self.server.gui.edit_state(),
            "state": app.status_text(),
            "hotkey": settings.get("hotkey", "ctrl+alt+space"),
            "sttModel": settings.get("stt", {}).get("model", "base.en"),
            "cleanupEnabled": bool(settings.get("cleanup", {}).get("enabled", False)),
            "cleanupModel": settings.get("cleanup", {}).get("model", "gemma3:1b"),
            "insertionMode": insertion.get("mode", "auto"),
            "inputDeviceId": "default" if recording.get("input_device_id") is None else str(recording.get("input_device_id")),
            "gainDb": recording.get("gain_db", 0.0),
            "silenceEnabled": bool(silence.get("enabled", True)),
            "silenceSeconds": silence.get("silence_seconds", 1.4),
            "speechThreshold": silence.get("speech_threshold", 0.012),
            "lastTranscriptAvailable": bool(getattr(app, "last_transcript", "")),
            "lastResult": result_payload,
            "settingsPath": str(settings_path()),
            "setup": self._setup_payload(settings),
        }

    def _setup_payload(self, settings: dict[str, Any] | None = None) -> dict[str, Any]:
        status = collect_setup_status(settings, include_stt=True, include_ollama=False)
        return {
            "ok": status.ok,
            "steps": [step.__dict__ for step in status.steps],
        }

    def _update_settings(self, payload: dict[str, Any]) -> None:
      current = load_settings(create=True)
      insertion = current.get("insertion", {})
      recording = current.get("recording", {})
      silence = recording.get("silence_stop", {})
      updated = update_settings(
        current,
        hotkey=str(payload.get("hotkey", current.get("hotkey", "ctrl+alt+space"))),
        stt_model=str(payload.get("sttModel", current.get("stt", {}).get("model", "base.en"))),
        cleanup_enabled=bool(payload.get("cleanupEnabled", current.get("cleanup", {}).get("enabled", False))),
        cleanup_model=str(payload.get("cleanupModel", current.get("cleanup", {}).get("model", "gemma3:1b"))),
        insertion_mode=str(payload.get("insertionMode", insertion.get("mode", "auto"))),
        input_device_id=str(payload.get("inputDeviceId", recording.get("input_device_id") or "default")),
        gain_db=str(payload.get("gainDb", recording.get("gain_db", 0.0))),
        silence_enabled=bool(payload.get("silenceEnabled", silence.get("enabled", True))),
        silence_seconds=str(payload.get("silenceSeconds", silence.get("silence_seconds", 1.4))),
        speech_threshold=str(payload.get("speechThreshold", silence.get("speech_threshold", 0.012))),
        startup_enabled=bool(current.get("startup", {}).get("enabled", False)),
      )
      save_settings(updated)
      self.server.gui.app.reload_settings(force=True)
      if self.server.gui.edit_state()["editMode"]:
        result = self.server.gui.exit_edit_mode()
        if not result.ok:
          raise BusyError(result.message)

    def _update_edit_mode(self, payload: dict[str, Any]) -> None:
        enabled = payload.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("Edit mode enabled value must be true or false.")
        result = self.server.gui.enter_edit_mode() if enabled else self.server.gui.exit_edit_mode()
        if not result.ok:
            raise BusyError(result.message)
        self._send_json({**self._state_payload(), "message": result.message})

    def _update_runtime(self, payload: dict[str, Any]) -> None:
        enabled = payload.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("Runtime enabled value must be true or false.")
        app = self.server.gui.app
        result = app.enable_runtime() if enabled else app.disable_runtime()
        if not result.ok:
            raise BusyError(result.message)
        self._send_json({**self._state_payload(), "message": result.message})

    def _toggle_recording(self) -> None:
        app = self.server.gui.app
        if not app.runtime_enabled():
            raise BusyError("Dictation runtime is disabled.")
        if app.status_text() == "PROCESSING":
            raise BusyError("Dictation is processing the current recording.")
        app.handle_hotkey()
        self._send_json(self._state_payload())

    def _send_html(self, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(data)

    def _send_security_headers(self) -> None:
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)

    def _send_error(self, status: int, message: str) -> None:
        self._send_json({"error": message}, status=status)


class BusyError(RuntimeError):
    pass


def _page_html(token: str, url: str) -> str:
    token_json = json.dumps(token)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Local Dictation</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f1eb;
      --surface: #fffdf8;
      --ink: #1d2528;
      --muted: #657174;
      --line: #d8d0c3;
      --accent: #0f766e;
      --accent-strong: #0b5f59;
      --danger: #b42318;
      --disabled: #9aa4a6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: linear-gradient(135deg, #f4f1eb 0%, #e8f0ed 48%, #f9f5ec 100%);
      color: var(--ink);
      font-family: Candara, Avenir Next, Segoe UI, sans-serif;
      min-height: 100vh;
    }}
    main {{ max-width: 980px; margin: 0 auto; padding: 28px; }}
    header {{ display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; margin-bottom: 22px; }}
    h1 {{ font-size: 30px; margin: 0 0 6px; font-weight: 700; }}
    .url {{ color: var(--muted); font-size: 14px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    section {{ background: rgba(255, 253, 248, 0.9); border: 1px solid var(--line); border-radius: 8px; padding: 18px; box-shadow: 0 12px 32px rgba(38, 45, 48, 0.08); }}
    h2 {{ font-size: 18px; margin: 0 0 14px; }}
    label {{ display: block; color: var(--muted); font-size: 13px; margin: 12px 0 6px; }}
    input, select {{ width: 100%; min-height: 38px; border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; font: inherit; background: white; color: var(--ink); }}
    input[type=\"checkbox\"] {{ width: auto; min-height: auto; margin-right: 8px; }}
    button {{ border: 0; border-radius: 6px; min-height: 38px; padding: 8px 13px; font: inherit; font-weight: 700; color: white; background: var(--accent); cursor: pointer; }}
    button:hover {{ background: var(--accent-strong); }}
    button.secondary {{ background: #475569; }}
    button.danger {{ background: var(--danger); }}
    button:disabled {{ background: var(--disabled); cursor: not-allowed; }}
    .row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
    .pill {{ display: inline-flex; align-items: center; min-height: 30px; padding: 4px 10px; border-radius: 999px; background: #d9efe8; color: #0f4f48; font-weight: 700; }}
    .pill.off {{ background: #eee5dc; color: #684b37; }}
    .message {{ min-height: 22px; color: var(--muted); font-size: 14px; margin-top: 14px; }}
    .message.error {{ color: var(--danger); }}
    .path {{ word-break: break-all; color: var(--muted); font-size: 13px; margin-top: 12px; }}
    @media (max-width: 760px) {{
      main {{ padding: 18px; }}
      header {{ display: block; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Local Dictation</h1>
        <div class="url">{url}</div>
      </div>
      <div id=\"runtime-pill\" class=\"pill off\">Loading</div>
    </header>
    <div class=\"grid\">
      <section>
        <h2>Status</h2>
        <div class=\"row\">
          <span id=\"state-pill\" class=\"pill\">IDLE</span>
          <span id=\"transcript-pill\" class=\"pill off\">No transcript</span>
          <span id=\"setup-pill\" class=\"pill off\">Speech model</span>
        </div>
        <div id=\"last-result\" class=\"message\"></div>
        <div id=\"settings-path\" class=\"path\"></div>
      </section>
      <section>
        <h2>Runtime</h2>
        <div class=\"row\">
          <button id=\"runtime-button\">Turn On</button>
          <button id=\"record-button\" class=\"secondary\">Start Recording</button>
          <button id=\"edit-mode-button\" class=\"secondary\">Edit Settings</button>
        </div>
      </section>
      <section>
        <h2>Hotkey</h2>
        <label for=\"hotkey\">Binding</label>
        <input id=\"hotkey\" autocomplete=\"off\" spellcheck=\"false\">
        <label for=\"insertion-mode\">Insertion</label>
        <select id=\"insertion-mode\">
          <option>auto</option>
          <option>direct</option>
          <option>clipboard</option>
        </select>
      </section>
      <section>
        <h2>Models</h2>
        <label for=\"stt-model\">Speech model</label>
        <select id=\"stt-model\">
          <option>tiny.en</option>
          <option>base.en</option>
          <option>small.en</option>
          <option>medium.en</option>
        </select>
        <label><input id=\"cleanup-enabled\" type=\"checkbox\">Use cleanup</label>
        <label for=\"cleanup-model\">Cleanup model</label>
        <input id=\"cleanup-model\" autocomplete=\"off\" spellcheck=\"false\">
      </section>
      <section>
        <h2>Audio</h2>
        <label for=\"input-device\">Input device</label>
        <input id=\"input-device\" autocomplete=\"off\" spellcheck=\"false\">
        <label for=\"gain-db\">Microphone gain dB</label>
        <input id=\"gain-db\" autocomplete=\"off\" spellcheck=\"false\">
        <label><input id=\"silence-enabled\" type=\"checkbox\">Stop after silence</label>
        <label for=\"silence-seconds\">Silence seconds</label>
        <input id=\"silence-seconds\" autocomplete=\"off\" spellcheck=\"false\">
        <label for=\"speech-threshold\">Speech threshold</label>
        <input id=\"speech-threshold\" autocomplete=\"off\" spellcheck=\"false\">
      </section>
    </div>
    <div class=\"row\" style=\"margin-top: 14px; justify-content: flex-end;\">
      <button id=\"save-button\">Save Settings</button>
      <button id=\"cancel-edit-button\" class=\"secondary\" style=\"display: none;\">Cancel</button>
    </div>
    <div id=\"message\" class=\"message\"></div>
  </main>
  <script>
    const token = {token_json};
    let state = null;

    const $ = (id) => document.getElementById(id);
    const message = (text, isError = false) => {{
      const node = $("message");
      node.textContent = text || "";
      node.className = isError ? "message error" : "message";
    }};
    const request = async (url, options = {{}}) => {{
      const response = await fetch(url, {{ cache: "no-store", ...options }});
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "Request failed");
      return body;
    }};
    const post = (url, body = {{}}) => request(url, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json", "X-Local-Dictation-Token": token }},
      body: JSON.stringify(body),
    }});
    const settingsPayload = () => ({{
      hotkey: $("hotkey").value,
      sttModel: $("stt-model").value,
      cleanupEnabled: $("cleanup-enabled").checked,
      cleanupModel: $("cleanup-model").value,
      insertionMode: $("insertion-mode").value,
      inputDeviceId: $("input-device").value,
      gainDb: $("gain-db").value,
      silenceEnabled: $("silence-enabled").checked,
      silenceSeconds: $("silence-seconds").value,
      speechThreshold: $("speech-threshold").value,
    }});
    const renderSettings = (next) => {{
      $("hotkey").value = next.hotkey;
      $("stt-model").value = next.sttModel;
      $("cleanup-enabled").checked = next.cleanupEnabled;
      $("cleanup-model").value = next.cleanupModel;
      $("insertion-mode").value = next.insertionMode;
      $("input-device").value = next.inputDeviceId;
      $("gain-db").value = next.gainDb;
      $("silence-enabled").checked = next.silenceEnabled;
      $("silence-seconds").value = next.silenceSeconds;
      $("speech-threshold").value = next.speechThreshold;
    }};
    const render = (next, options = {{}}) => {{
      const preserveSettings = options.preserveSettings ?? state?.editMode === true;
      state = next;
      const editMode = state.editMode === true;
      $("runtime-pill").textContent = state.runtimeEnabled ? "Runtime On" : "Runtime Off";
      $("runtime-pill").className = state.runtimeEnabled ? "pill" : "pill off";
      $("state-pill").textContent = state.state;
      $("transcript-pill").textContent = state.lastTranscriptAvailable ? "Transcript ready" : "No transcript";
      $("transcript-pill").className = state.lastTranscriptAvailable ? "pill" : "pill off";
      $("setup-pill").textContent = state.setup?.ok ? "Speech model ready" : "Speech model not ready";
      $("setup-pill").className = state.setup?.ok ? "pill" : "pill off";
      $("last-result").textContent = state.lastResult?.message || "";
      $("last-result").className = state.lastResult?.ok ? "message" : "message error";
      $("runtime-button").textContent = state.runtimeEnabled ? "Turn Off" : "Turn On";
      $("runtime-button").className = state.runtimeEnabled ? "danger" : "";
      $("runtime-button").disabled = editMode;
      $("record-button").textContent = state.state === "RECORDING" ? "Stop Recording" : "Start Recording";
      $("record-button").disabled = editMode || !state.runtimeEnabled || state.state === "PROCESSING";
      $("edit-mode-button").textContent = editMode ? "Editing Settings" : "Edit Settings";
      $("edit-mode-button").disabled = editMode;
      $("save-button").textContent = editMode ? "Save and Resume" : "Save Settings";
      $("cancel-edit-button").style.display = editMode ? "" : "none";
      if (!preserveSettings) renderSettings(state);
      $("settings-path").textContent = state.settingsPath;
    }};
    const refresh = async () => render(await request("/api/state"));

    $("edit-mode-button").addEventListener("click", async () => {{
      try {{
        render(await post("/api/edit-mode", {{ enabled: true }}));
        message("Edit mode enabled. Dictation listening is paused while you edit.");
      }} catch (error) {{ message(error.message, true); }}
    }});

    $("save-button").addEventListener("click", async () => {{
      try {{
        const wasEditing = state?.editMode === true;
        render(await post("/api/settings", settingsPayload()), {{ preserveSettings: false }});
        message(wasEditing ? "Settings saved and runtime restored." : "Settings saved and applied.");
      }} catch (error) {{ message(error.message, true); }}
    }});
    $("cancel-edit-button").addEventListener("click", async () => {{
      try {{
        render(await post("/api/edit-mode", {{ enabled: false }}), {{ preserveSettings: false }});
        message("Edit mode closed.");
      }} catch (error) {{ message(error.message, true); }}
    }});
    $("runtime-button").addEventListener("click", async () => {{
      try {{
        render(await post("/api/runtime", {{ enabled: !state.runtimeEnabled }}));
        message(state.runtimeEnabled ? "Runtime enabled." : "Runtime disabled.");
      }} catch (error) {{ message(error.message, true); }}
    }});
    $("record-button").addEventListener("click", async () => {{
      try {{
        render(await post("/api/recording"));
        message("");
      }} catch (error) {{ message(error.message, true); }}
    }});
    refresh().catch((error) => message(error.message, true));
    setInterval(() => {{
      if (state?.editMode !== true) refresh().catch(() => {{}});
    }}, 2000);
  </script>
</body>
</html>"""