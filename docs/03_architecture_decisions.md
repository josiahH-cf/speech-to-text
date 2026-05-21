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

## Decision 8: Core-First Setup

Prepare the local speech-to-text model separately from optional Ollama cleanup setup.

Reasoning:
- Raw local dictation is the core product path and should not report failure only because optional cleanup is absent.
- Ollama installation and model pulls can take longer, require more dependencies, and are not needed for useful transcription.
- Setup commands can still prepare both layers, but installer defaults and setup status should keep the core path clear.

## Decision 9: Embedded Local Control UI

Host the browser control UI inside the existing resident app process, preferring `http://127.0.0.1:8765/` and recovering to a nearby loopback port when the preferred port is busy.

Reasoning:
- `LocalDictation.exe run` already owns the tray icon, global hotkey, settings reload loop, and dictation runtime.
- Keeping the localhost UI in that same process avoids a second daemon, service registration, or separate IPC layer.
- The preferred loopback address gives users and support docs one stable default, while automatic fallback avoids losing the browser UI to unrelated local port conflicts.
- Runtime off means dictation listening is disabled; it does not quit the tray process or disable startup-on-login.
- The control UI should write the existing settings file and call the existing runtime seams rather than creating parallel configuration paths.
