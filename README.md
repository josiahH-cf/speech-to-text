# Local Dictation

Minimal Windows 11 local dictation tray app.

Press a global hotkey, speak into the default microphone, press the hotkey again, and the app transcribes locally with `faster-whisper`. Optional cleanup can run through a local Ollama model. The final text is typed into the window that was focused when recording started, with clipboard paste as a fallback.

## What It Builds

- Resident tray app.
- Configurable global hotkey.
- Default microphone recording.
- Local `faster-whisper` transcription.
- Optional Ollama cleanup at `http://localhost:11434`.
- Direct Unicode typing into the previous target window, with clipboard paste fallback.
- Current-user startup integration.
- Settings and logs under `%APPDATA%\LocalDictation`.

## Install

### User Install From Built Installer

After building the installer, run:

```powershell
.\dist\installer\LocalDictationSetup-0.2.0.exe
```

The installer is per-user and installs to:

```text
%LOCALAPPDATA%\Programs\LocalDictation
```

It creates Start Menu shortcuts for the app, settings, and doctor. During setup, the optional bootstrap step prepares the speech model and can install Ollama through winget.

### Developer Install From Source

Open PowerShell in this repo and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

If PowerShell blocks activation scripts, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then retry activation.

## Build The Installer

```powershell
.\scripts\build-installer.ps1
```

If Inno Setup is not installed, either install it manually or let the build script install it with winget:

```powershell
.\scripts\build-installer.ps1 -InstallTools
```

To build only the PyInstaller app bundle:

```powershell
.\scripts\build-installer.ps1 -SkipInstaller
```

Outputs:

```text
dist\LocalDictation\LocalDictation.exe
dist\LocalDictation\LocalDictationCLI.exe
dist\installer\LocalDictationSetup-0.2.0.exe
```

## Prepare The STT Model

The first model download needs internet. Transcription after the model is cached is local.

```powershell
python -m local_dictation download-model
```

For the packaged app:

```powershell
LocalDictationCLI.exe setup bootstrap
```

Default model: `base.en`.

For a faster but lower-quality model, edit `%APPDATA%\LocalDictation\settings.json` and set:

```json
{
  "stt": {
    "model": "tiny.en"
  }
}
```

For better quality on stronger hardware, try:

```json
{
  "stt": {
    "model": "small.en"
  }
}
```

## Run

```powershell
python -m local_dictation run
```

The app appears in the system tray. Default hotkey:

```text
Ctrl+Alt+Space
```

Workflow:

1. Put your cursor in a text field.
2. Press `Ctrl+Alt+Space`.
3. Speak.
4. Press `Ctrl+Alt+Space` again.
5. Wait for the transcription to appear.

For console debugging without the tray:

```powershell
python -m local_dictation run --no-tray
```

Packaged app commands:

```powershell
LocalDictation.exe run
LocalDictation.exe settings
LocalDictationCLI.exe doctor
LocalDictationCLI.exe setup bootstrap
LocalDictationCLI.exe setup status
LocalDictationCLI.exe transcribe-file sample.wav
LocalDictationCLI.exe insert-test --text "Local Dictation insert test"
```

## Configure

Settings file:

```text
%APPDATA%\LocalDictation\settings.json
```

The file is created on first run. Default settings:

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

Settings can also be edited from the tray menu. Safe changes are reloaded by the resident app before the next recording; hotkey changes are re-registered when the app is idle.

## Optional Ollama Cleanup

Bootstrap can install Ollama through winget and pull the configured local model:

```powershell
python -m local_dictation setup bootstrap
```

Enable cleanup in settings:

```json
{
  "cleanup": {
    "enabled": true,
    "provider": "ollama",
    "endpoint": "http://localhost:11434/api/generate",
    "model": "gemma3:1b",
    "mode": "punctuate",
    "timeout_seconds": 20
  }
}
```

If Ollama is unavailable, the app logs the failure and uses the raw transcript.

## Startup On Login

Enable:

```powershell
python -m local_dictation startup enable
```

Disable:

```powershell
python -m local_dictation startup disable
```

Check status:

```powershell
python -m local_dictation startup status
```

This uses the current user's Windows Run registry entry and does not require administrator rights.

## Test And Diagnose

Run automated tests:

```powershell
python -m pytest
```

Run setup diagnostics:

```powershell
python -m local_dictation doctor
```

Run the scripted smoke checklist:

```powershell
.\scripts\smoke-test.ps1
```

Manual smoke test:

1. Run the app.
2. Open Notepad.
3. Click in the document.
4. Press `Ctrl+Alt+Space`.
5. Say: `this is a local dictation test`.
6. Press `Ctrl+Alt+Space`.
7. Confirm text appears in Notepad.

Repeat in a browser text box and an editor field.

## Logs

Logs are written here:

```text
%APPDATA%\LocalDictation\logs\local-dictation.log
```

The tray menu includes `Open Logs`.

## Troubleshooting

- Hotkey does nothing: run `python -m local_dictation doctor`; another app may own the hotkey. Change `hotkey` in settings.
- No microphone: check Windows privacy settings, default input device, and the `doctor` output.
- First transcription is slow: the model may be downloading or loading. Use `tiny.en` for faster startup.
- Cleanup does not run: confirm Ollama is installed, running, and has the configured model pulled.
- Text does not appear: the target may block focus restoration or simulated input. The final text should remain on the clipboard.
- Elevated target app does not accept input: the app detects likely integrity-level blocking and leaves the final text recoverable instead of blindly inserting into another target.
- `Application Control policy has blocked this file`: Windows security policy blocked a native dependency such as `tokenizers`. Run `python -m local_dictation doctor` from the installed environment, then allow the blocked file/location or use an environment approved by your policy.

## Known Limitations

- First model download may require internet.
- Bootstrap may require internet for the STT model, Ollama, and the Ollama cleanup model.
- Clipboard fallback attempts to preserve common text, file-drop, and bitmap clipboard formats, but unusual/private formats may not restore.
- Some elevated, protected, remote, game, or virtualized targets may reject simulated input.
- Elevated/protected target support is fail-safe, not privileged UIAccess.
