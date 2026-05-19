# Implementation Plan

## Order

1. Create governance documentation.
2. Add package metadata and dependency pins.
3. Implement configuration loading and default file creation.
4. Implement logging.
5. Implement hotkey parsing and Win32 registration.
6. Implement microphone recording.
7. Implement `faster-whisper` transcription.
8. Implement optional Ollama cleanup.
9. Implement focus capture, direct typing, integrity detection, and clipboard fallback insertion.
10. Implement startup enable/disable.
11. Implement tray runner and CLI commands.
12. Add README, tests, and diagnostics.
13. Add settings UI and setup bootstrap.
14. Add PyInstaller/Inno packaging.
15. Run automated tests, syntax checks, and packaging checks.

## Package Layout

- `src/local_dictation/config.py`: paths, defaults, load/save.
- `src/local_dictation/logging_config.py`: rotating file logging.
- `src/local_dictation/hotkey.py`: parser and Win32 hotkey listener.
- `src/local_dictation/recorder.py`: default microphone capture.
- `src/local_dictation/transcriber.py`: faster-whisper loading and transcription.
- `src/local_dictation/cleanup.py`: optional Ollama formatting.
- `src/local_dictation/insertion.py`: focus capture, direct typing, clipboard fallback.
- `src/local_dictation/settings_ui.py`: minimal graphical settings editor.
- `src/local_dictation/setup_manager.py`: STT/Ollama bootstrap and setup status.
- `src/local_dictation/startup.py`: HKCU Run integration.
- `src/local_dictation/app.py`: runtime state machine.
- `src/local_dictation/tray.py`: tray UI.
- `src/local_dictation/doctor.py`: diagnostics.
- `src/local_dictation/cli.py`: command routing.

## Runtime Flow

1. Load settings and initialize logs.
2. Register hotkey.
3. Start tray icon.
4. On first hotkey press:
   - Capture foreground window handle.
   - Start microphone recording.
5. On second hotkey press or max duration:
   - Stop recording.
   - Transcribe locally.
   - Optionally clean with Ollama.
   - Attempt focus restore.
   - Type final text directly, use clipboard fallback if needed, or leave it recoverable with a warning.
6. Return to idle.

## Error Handling

- Missing dependency: report in doctor and log at runtime.
- Hotkey conflict: fail startup with a clear message.
- Microphone unavailable: log error and remain idle.
- Empty recording or empty transcript: log and do not insert.
- Cleanup failure: log warning and use raw transcript.
- Focus or insertion failure: copy text to clipboard and log warning.
- Elevated/protected target: do not blindly insert; copy text to clipboard and log warning.
