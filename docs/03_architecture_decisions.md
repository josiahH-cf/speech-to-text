# Architecture Decisions

## Decision 1: Python Resident App

Use Python 3.12 as the app runtime.

Reasoning:
- Python 3.12 is available on the target machine.
- The machine has .NET runtimes but no .NET SDK, so a native .NET desktop build would add setup cost.
- Python has practical libraries for local STT, audio capture, Win32 calls, and tray UI.

## Decision 2: Lazy Runtime Imports

Import heavy and platform-specific dependencies only inside the modules/functions that need them.

Reasoning:
- `doctor`, config migration, and unit tests should run before all runtime dependencies are installed.
- Failures can be reported as targeted diagnostic messages instead of import-time crashes.

## Decision 3: Explicit Runtime State Machine

Use `IDLE -> RECORDING -> PROCESSING -> IDLE`.

Reasoning:
- Dictation has mutually exclusive phases.
- Hotkey behavior is easy to reason about.
- Hotkey presses during processing can be safely ignored and logged.

## Decision 4: Direct Typing With Clipboard Fallback

Use direct Unicode `SendInput` typing first for normal targets, then clipboard paste fallback.

Reasoning:
- Direct Unicode typing avoids changing the clipboard for common text targets.
- Clipboard paste remains useful where direct typing is blocked or unreliable.
- Windows UIPI can block input into higher-integrity targets, so target integrity is checked before injection.

## Decision 5: Ollama Optional

Cleanup is optional and disabled by default.

Reasoning:
- The core app must work without any local LLM runner installed.
- If the cleanup runner fails, raw transcription is still useful.
- Ollama has a stable local HTTP API and simple model naming.

## Decision 6: Current-User Startup

Use HKCU Run registry entry for startup integration.

Reasoning:
- It requires no administrator rights.
- It is simple to enable, disable, and inspect.
- It matches the app's single-user local-first purpose.

## Decision 7: Per-User Installer

Use PyInstaller for the app bundle and Inno Setup for a per-user Windows installer.

Reasoning:
- The installed app should run without an activated Python environment.
- Per-user install avoids administrator rights for the core app.
- Inno Setup is a maintained Windows installer builder and is available through winget.
