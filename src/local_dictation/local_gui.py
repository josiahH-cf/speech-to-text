from __future__ import annotations

import json
import logging
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .config import load_settings, save_settings, settings_path
from .settings_actions import update_core_settings
from .setup_manager import collect_setup_status

LOCAL_GUI_HOST = "127.0.0.1"
LOCAL_GUI_PORT = 8765
LOCAL_GUI_URL = f"http://{LOCAL_GUI_HOST}:{LOCAL_GUI_PORT}/"
MAX_JSON_BYTES = 16 * 1024


class LocalGuiServer:
    def __init__(self, app, *, logger: logging.Logger | None = None) -> None:
        self.app = app
        self.logger = logger or logging.getLogger(__name__)
        self.token = secrets.token_urlsafe(24)
        self._server: _LocalGuiHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return LOCAL_GUI_URL

    def start(self) -> bool:
        if self._server is not None:
            return True
        try:
            server = _LocalGuiHTTPServer((LOCAL_GUI_HOST, LOCAL_GUI_PORT), _LocalGuiHandler, self)
        except OSError as exc:
            self.logger.warning("Localhost GUI could not bind %s: %s", LOCAL_GUI_URL, exc)
            return False
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, name="localhost-gui", daemon=True)
        self._thread.start()
        self.logger.info("Localhost GUI listening at %s", LOCAL_GUI_URL)
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
        self.logger.info("Localhost GUI stopped.")

    def open_browser(self) -> None:
        webbrowser.open(LOCAL_GUI_URL)


class _LocalGuiHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

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
            self._send_html(_page_html(self.server.gui.token))
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
        self._send_error(404, "Not found.")

    def do_POST(self) -> None:
        if self.headers.get("X-Local-Dictation-Token") != self.server.gui.token:
            self._send_error(403, "Invalid local GUI token.")
            return

        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/settings":
                self._update_settings(payload)
                self._send_json(self._state_payload())
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

    def _state_payload(self) -> dict[str, Any]:
        app = self.server.gui.app
        settings = load_settings(create=True)
        return {
            "running": True,
            "runtimeEnabled": app.runtime_enabled(),
            "state": app.status_text(),
            "hotkey": settings.get("hotkey", "ctrl+alt+space"),
            "sttModel": settings.get("stt", {}).get("model", "base.en"),
            "cleanupEnabled": bool(settings.get("cleanup", {}).get("enabled", False)),
            "cleanupModel": settings.get("cleanup", {}).get("model", "gemma3:1b"),
            "lastTranscriptAvailable": bool(getattr(app, "last_transcript", "")),
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
        updated = update_core_settings(
            current,
            hotkey=str(payload.get("hotkey", current.get("hotkey", "ctrl+alt+space"))),
            stt_model=str(payload.get("sttModel", current.get("stt", {}).get("model", "base.en"))),
            cleanup_enabled=bool(payload.get("cleanupEnabled", current.get("cleanup", {}).get("enabled", False))),
            cleanup_model=str(payload.get("cleanupModel", current.get("cleanup", {}).get("model", "gemma3:1b"))),
        )
        save_settings(updated)
        self.server.gui.app.reload_settings(force=True)

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
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, status: int, message: str) -> None:
        self._send_json({"error": message}, status=status)


class BusyError(RuntimeError):
    pass


def _page_html(token: str) -> str:
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
        <div class=\"url\">{LOCAL_GUI_URL}</div>
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
        <div id=\"settings-path\" class=\"path\"></div>
      </section>
      <section>
        <h2>Runtime</h2>
        <div class=\"row\">
          <button id=\"runtime-button\">Turn On</button>
          <button id=\"record-button\" class=\"secondary\">Start Recording</button>
        </div>
      </section>
      <section>
        <h2>Hotkey</h2>
        <label for=\"hotkey\">Binding</label>
        <input id=\"hotkey\" autocomplete=\"off\" spellcheck=\"false\">
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
    </div>
    <div class=\"row\" style=\"margin-top: 14px; justify-content: flex-end;\">
      <button id=\"save-button\">Save Settings</button>
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
    const render = (next) => {{
      state = next;
      $("runtime-pill").textContent = state.runtimeEnabled ? "Runtime On" : "Runtime Off";
      $("runtime-pill").className = state.runtimeEnabled ? "pill" : "pill off";
      $("state-pill").textContent = state.state;
      $("transcript-pill").textContent = state.lastTranscriptAvailable ? "Transcript ready" : "No transcript";
      $("transcript-pill").className = state.lastTranscriptAvailable ? "pill" : "pill off";
      $("setup-pill").textContent = state.setup?.ok ? "Speech model ready" : "Speech model not ready";
      $("setup-pill").className = state.setup?.ok ? "pill" : "pill off";
      $("runtime-button").textContent = state.runtimeEnabled ? "Turn Off" : "Turn On";
      $("runtime-button").className = state.runtimeEnabled ? "danger" : "";
      $("record-button").textContent = state.state === "RECORDING" ? "Stop Recording" : "Start Recording";
      $("record-button").disabled = !state.runtimeEnabled || state.state === "PROCESSING";
      $("hotkey").value = state.hotkey;
      $("stt-model").value = state.sttModel;
      $("cleanup-enabled").checked = state.cleanupEnabled;
      $("cleanup-model").value = state.cleanupModel;
      $("settings-path").textContent = state.settingsPath;
    }};
    const refresh = async () => render(await request("/api/state"));

    $("save-button").addEventListener("click", async () => {{
      try {{
        render(await post("/api/settings", {{
          hotkey: $("hotkey").value,
          sttModel: $("stt-model").value,
          cleanupEnabled: $("cleanup-enabled").checked,
          cleanupModel: $("cleanup-model").value,
        }}));
        message("Settings saved.");
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
    setInterval(() => refresh().catch(() => {{}}), 2000);
  </script>
</body>
</html>"""