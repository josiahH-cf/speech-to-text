# Enterprise Security Review

This note is a concise behavior inventory for security reviewers evaluating Local Dictation on a managed Windows work device. It is defensive documentation only; it does not describe bypasses, stealth behavior, or security-control changes.

## Application Summary

Local Dictation is a Windows 11 per-user desktop utility. It runs as a visible tray application, records from the default microphone after a user action, transcribes locally with `faster-whisper`, optionally formats text through a configured Ollama endpoint, and inserts the final text into the window that was active when recording started.

The expected review triggers are normal for this category of utility: global hotkey registration, microphone access, simulated keyboard input, clipboard paste fallback, a resident tray process, an optional current-user Run entry, a loopback browser UI, PyInstaller-packaged native dependencies, and optional model or tool downloads during setup.

## Confirmed Behaviors

| Area | Behavior | Evidence |
| --- | --- | --- |
| Hotkey | Registers a Windows global hotkey and handles `WM_HOTKEY` in a background thread. | `src/local_dictation/hotkey.py`, `GlobalHotkeyListener` |
| Recording | Opens the default microphone with `sounddevice.InputStream` after the user starts recording. | `src/local_dictation/recorder.py`, `MicrophoneRecorder` |
| Transcription | Loads a local `faster-whisper` model and transcribes audio in process. | `src/local_dictation/transcriber.py`, `FasterWhisperTranscriber` |
| Optional cleanup | Sends transcript text to the configured Ollama-compatible endpoint when cleanup is enabled. The default endpoint is local. | `src/local_dictation/cleanup.py`, `cleanup_text` |
| Text insertion | Restores focus to the captured target window, sends Unicode keyboard input, and falls back to clipboard paste. | `src/local_dictation/insertion.py`, `insert_text` |
| Clipboard | Reads, writes, and restores common clipboard formats during fallback. | `src/local_dictation/insertion.py`, `snapshot_clipboard` |
| Local browser UI | Hosts a token-protected local UI on loopback, preferring `http://127.0.0.1:8765/` and recovering to a nearby port if needed. | `src/local_dictation/local_gui.py`, `LocalGuiServer` |
| Startup | Can write or remove `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\LocalDictation`. Startup is opt-in. | `src/local_dictation/startup.py` |
| Logs and settings | Stores settings and logs under `%APPDATA%\LocalDictation`. | `src/local_dictation/config.py`, `src/local_dictation/logging_config.py` |
| Installer | Installs per-user under `%LOCALAPPDATA%\Programs\LocalDictation`. | `packaging/LocalDictation.iss` |

## Network and Localhost Behavior

The app does not include telemetry or analytics endpoints in the reviewed source. Runtime network behavior is limited to these surfaces:

- Local browser UI: prefers `http://127.0.0.1:8765/`, bound to loopback, with nearby loopback fallback if the preferred port is busy.
- Optional cleanup: default `http://localhost:11434/api/generate`, disabled by default.
- Model preparation: `faster-whisper` may download model files through its normal model-loading path when `local_files_only` is false.
- Optional setup: `setup bootstrap --ollama-only` can call `winget install Ollama.Ollama` and `ollama pull <model>`.

When cleanup is configured with a non-local or unusual endpoint, the app logs a warning and continues with the user's configured value. This preserves existing behavior while making transcript egress risk visible for review.

## Local Browser UI Controls

The browser UI is served by the tray process, not a Windows service. POST endpoints require a per-session `X-Local-Dictation-Token`. Browser-origin POST requests are accepted only when the Origin header is absent or matches the local UI origin. HTML and JSON responses include conservative browser security headers.

The UI can view status, update core settings, turn dictation runtime on or off, and start or stop recording through the same application path used by the global hotkey.

## Packaging and Reputation Notes

Release builds are PyInstaller bundles distributed through an Inno Setup installer. UPX packing is disabled to improve static reviewability and reduce packed-binary reputation concerns. Build output can include `dist\release-evidence\` with checksums, build provenance, direct dependencies, and Authenticode signature status.

Unsigned artifacts may still draw reputation prompts on managed Windows devices. Signed artifacts are recommended for review and deployment, but local unsigned builds remain supported for development.

## Reviewer Checklist

- Verify the visible tray process and Quit control.
- Verify installer path: `%LOCALAPPDATA%\Programs\LocalDictation`.
- Verify settings/log path: `%APPDATA%\LocalDictation`.
- Verify optional startup value: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\LocalDictation`.
- Verify localhost UI binds to loopback at the preferred or recovered URL.
- Verify optional cleanup default endpoint is `localhost:11434` and cleanup is disabled by default.
- Verify release checksums and Authenticode signature status when provided.
- Verify no source-level telemetry endpoint is present in the reviewed version.

## Residual Risk

No source review can promise that endpoint protection, SmartScreen, application control, or EDR tooling will never flag the app. The app intentionally performs user-facing Windows automation, microphone recording, clipboard access, and model loading. Those behaviors should be reviewed as legitimate dictation functionality, supported by signing, transparent documentation, and predictable install paths.