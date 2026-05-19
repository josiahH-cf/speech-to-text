# Research Findings

Research date: 2026-05-19.

## Local Speech-To-Text Options

### faster-whisper

Source: https://github.com/SYSTRAN/faster-whisper and https://pypi.org/project/faster-whisper/

Findings:
- Current package version confirmed as `1.2.1`.
- It reimplements Whisper using CTranslate2.
- It supports loading models by model name or local directory.
- PyPI provides a Python wheel for the library itself; CTranslate2 publishes Windows x64 wheels for supported Python versions.
- It is a good fit for a Python MVP because it avoids building or shipping a separate STT binary.

Decision:
- Use `faster-whisper==1.2.1` for MVP.
- Default to CPU `int8` and `base.en` to reduce hardware assumptions.

### whisper.cpp

Source: https://github.com/ggml-org/whisper.cpp/releases

Findings:
- Active project with current releases and Windows binary assets.
- Strong fallback for users who want a standalone native binary path.
- Adds packaging complexity if embedded directly in a Python MVP because the app must manage executable discovery, model files, and CLI output parsing.

Decision:
- Keep as a documented fallback, not MVP default.

### Vosk

Source: https://github.com/alphacep/vosk-api

Findings:
- Offline speech recognition toolkit with small models and streaming APIs.
- Supports many languages and Python bindings.
- Latest release cadence is slower than faster-whisper and Whisper accuracy is generally more attractive for free-form dictation.

Decision:
- Do not use for MVP; keep as fallback if Whisper-class models are too heavy.

## Local Cleanup Runner

### Ollama

Source: https://docs.ollama.com/api/introduction

Findings:
- Default local API base URL is `http://localhost:11434/api`.
- `/api/generate` can be called with `stream: false`.
- Official local model runner with simple installation and model management.

Decision:
- Use Ollama as the optional cleanup path.
- Cleanup is disabled by default so the dictation app remains useful without Ollama installed.
- Default cleanup model is `gemma3:1b`, configurable.

## Windows And Desktop Integration

### Global hotkey

Source: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey

Findings:
- `RegisterHotKey` defines a system-wide hotkey and posts `WM_HOTKEY` to a message loop.
- The API reports failure when a hotkey conflicts or registration is invalid.
- `MOD_NOREPEAT` prevents repeated notifications while the keys are held.

Decision:
- Use `RegisterHotKey` through `pywin32`.

### Focus tracking and restoration

Sources:
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getforegroundwindow
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow

Findings:
- `GetForegroundWindow` returns the active foreground window handle.
- `SetForegroundWindow` can be denied by Windows foreground restrictions.

Decision:
- Capture foreground window when recording starts.
- Attempt restore before insertion.
- If restore fails, copy final text to clipboard and log a warning rather than inserting into an unsafe target.

### Text insertion

Sources:
- https://learn.microsoft.com/en-gb/windows/win32/api/winuser/nf-winuser-sendinput
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-openclipboard
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setclipboarddata

Findings:
- `SendInput` synthesizes keyboard input but may be blocked by integrity-level rules.
- Clipboard operations require opening and closing the clipboard correctly.

Decision:
- Use direct Unicode `SendInput` typing first for normal targets.
- Use clipboard paste as a fallback path, including `Ctrl+V`, when direct typing fails or is disabled.
- Check target integrity before injection because UIPI can block higher-integrity targets.

### Microphone capture

Source: https://python-sounddevice.readthedocs.io/en/0.3.14/api.html

Findings:
- `sounddevice` exposes default input device settings and PortAudio input streams.
- `InputStream` supports callback-based recording from the default device.

Decision:
- Use `sounddevice.InputStream` with mono `float32` samples and a 16 kHz default sample rate.

### Tray UI

Source: https://pystray.readthedocs.io/en/latest/usage.html

Findings:
- `pystray` provides Windows tray icon and menu support from Python.

Decision:
- Use `pystray` for a minimal resident UI: status, open settings, open logs, run doctor, quit.

### Startup behavior

Source: https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys

Findings:
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` starts a program at user logon.
- Windows may delay startup entries and execution order is not guaranteed.

Decision:
- Use the HKCU Run key for per-user startup without admin rights.

## Packaging And Installation

### PyInstaller

Source: https://pyinstaller.org/en/stable/

Findings:
- PyInstaller bundles a Python application and dependencies so users do not need to install Python packages manually.
- Windows bundles must be built on Windows.
- PyInstaller supports spec files for repeatable builds and hidden import/data collection.

Decision:
- Use `pyinstaller==6.20.0` to build `LocalDictation.exe`.
- Use one-folder packaging first because local ML dependencies are large and easier to inspect than a one-file extractor bundle.

### Inno Setup

Source: https://jrsoftware.org/isinfo.php and local `winget show JRSoftware.InnoSetup`.

Findings:
- Inno Setup is an open-source Windows installer builder.
- `JRSoftware.InnoSetup` is available through winget.

Decision:
- Use an Inno Setup script to create `LocalDictationSetup-0.2.0.exe`.
- Install per-user under `%LOCALAPPDATA%\Programs\LocalDictation`.

### Ollama winget package

Source: local `winget show Ollama.Ollama`.

Findings:
- `Ollama.Ollama` is available through winget.
- The current local package metadata reports Ollama `0.24.0` and an Inno installer.

Decision:
- Setup bootstrap attempts `winget install --id Ollama.Ollama --exact --silent`.
- After install or detection, setup bootstrap runs `ollama pull` for the configured cleanup model.
