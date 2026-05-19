# Definition Of Done

The MVP is done when all of these are true:

- Governance docs exist and reflect implementation decisions.
- `README.md` explains install, run, configuration, startup, troubleshooting, and known limitations.
- `pyproject.toml` pins MVP dependencies.
- `python -m local_dictation doctor` runs without crashing.
- `python -m local_dictation run` starts the resident app when dependencies are installed.
- Config file is created automatically on first run.
- A per-user installer can be built.
- The packaged app can run without an activated Python environment.
- The settings window can update the main configuration file.
- Silence auto-stop can finish a recording after speech has started.
- Normal text targets use direct Unicode typing before clipboard fallback.
- Elevated/protected targets fail safe with recoverable text.
- Setup bootstrap can prepare the STT model and attempt Ollama setup through winget.
- Hotkey can start and stop recording.
- Recording uses the default microphone.
- Transcription uses `faster-whisper` locally.
- Cleanup is optional through Ollama and fails open to raw transcript.
- Insertion uses target focus restore plus direct Unicode typing, with clipboard paste fallback.
- Startup can be enabled and disabled for the current user.
- Logs are written for major workflow steps and failures.
- Automated tests cover non-hardware logic.
- Syntax checks and available tests pass.

Known acceptable v0.2 limitations:

- First STT model download may need internet.
- Bootstrap may need internet for Ollama and cleanup model download.
- Tray icon and settings UI are minimal.
- Clipboard fallback may not preserve unusual/private clipboard formats.
- Some elevated or protected targets may block insertion.
