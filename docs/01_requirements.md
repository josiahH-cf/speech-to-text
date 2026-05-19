# Requirements

## Functional Requirements

- Windows 11 x64 desktop app behavior.
- Resident tray/background process.
- Configurable global hotkey with a safe default: `ctrl+alt+space`.
- Toggle recording with the same hotkey.
- Capture from the default Windows microphone.
- Transcribe locally with a configurable `faster-whisper` model.
- Optional cleanup through Ollama on localhost.
- Capture foreground window before recording and attempt to restore it before insertion.
- Insert final text with direct Unicode typing by default, using clipboard paste fallback when needed.
- Provide startup enable/disable through the current user's Windows startup registry key.
- Provide a per-user Windows installer.
- Provide a settings window.
- Provide silence auto-stop.
- Provide diagnostics through a `doctor` command.
- Provide install, run, configuration, troubleshooting, and known limitation docs.

## Technical Requirements

- Runtime language: Python 3.12.
- Package layout: `src/local_dictation`.
- Configuration path: `%APPDATA%\LocalDictation\settings.json`.
- Logs path: `%APPDATA%\LocalDictation\logs`.
- STT dependency: `faster-whisper==1.2.1`.
- Microphone dependency: `sounddevice==0.5.5`.
- Windows API dependency: `pywin32==311`.
- Tray dependency: `pystray==0.19.5` and `Pillow==12.2.0`.
- Local cleanup: Ollama HTTP API at `http://localhost:11434/api/generate`.
- Startup location: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.

## Default Settings

```json
{
  "hotkey": "ctrl+alt+space",
  "recording": {
    "sample_rate": 16000,
    "channels": 1,
    "max_seconds": 120,
    "silence_stop": {
      "enabled": true,
      "min_recording_seconds": 1.5,
      "speech_threshold": 0.012,
      "silence_seconds": 1.4
    }
  },
  "stt": { "engine": "faster-whisper", "model": "base.en", "device": "cpu", "compute_type": "int8", "language": "en", "vad_filter": true, "local_files_only": false },
  "cleanup": { "enabled": false, "provider": "ollama", "endpoint": "http://localhost:11434/api/generate", "model": "gemma3:1b", "mode": "punctuate", "timeout_seconds": 20 },
  "insertion": {
    "mode": "auto",
    "restore_clipboard_text": true,
    "focus_restore_timeout_ms": 700,
    "direct_typing_delay_ms": 1,
    "clipboard_fallback": true,
    "preserve_clipboard_formats": true,
    "copy_on_failure": true
  },
  "startup": { "enabled": false },
  "setup": { "stt_model_ready": false, "ollama_install": "auto", "ollama_ready": false, "last_bootstrap_status": null },
  "logging": { "level": "INFO", "keep_files": 5 }
}
```

## Acceptance Criteria

- First run creates the settings file and log directory.
- `python -m local_dictation doctor` reports environment readiness.
- `python -m local_dictation run` starts a resident process.
- The default hotkey records and stops recording.
- A valid microphone recording is transcribed locally.
- If cleanup is disabled, raw transcript is inserted.
- If cleanup is enabled but Ollama fails, raw transcript is inserted and the failure is logged.
- Startup enable/disable writes/removes only the app's current-user Run entry.
- Installer builds a per-user setup executable.
- Setup bootstrap prepares the speech model and attempts Ollama setup when configured.
