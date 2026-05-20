# Local Dictation

Minimal Windows 11 local dictation tray app.

Press a global hotkey, speak into the default microphone, press the hotkey again, and the app transcribes locally with `faster-whisper`. Optional cleanup can run through a local Ollama model. The final text is typed into the window that was focused when recording started, with clipboard paste as a fallback.

## What It Does

- Resident tray app.
- Configurable global hotkey.
- Default microphone recording.
- Local `faster-whisper` transcription.
- Optional Ollama cleanup at `http://localhost:11434`.
- Direct Unicode typing into the previous target window, with clipboard paste fallback.
- Local browser control UI at `http://127.0.0.1:8765/`.
- Current-user startup integration.
- Settings and logs under `%APPDATA%\LocalDictation`.

## Quick Start For End Users

1. Run the installer.
2. Leave `Prepare speech model after install` checked.
3. Launch Local Dictation from the Start Menu.
4. Open `Open Localhost GUI` from the tray menu if you want to check runtime, settings, or speech-model readiness.
5. Put your cursor in a text field, press `Ctrl+Alt+Space`, speak, then press `Ctrl+Alt+Space` again.

Ollama cleanup is optional. The app should remain useful with only the speech model prepared.

## Install

### User Install From Built Installer

Run the installer file you received or built:

```powershell
.\dist\installer\LocalDictationSetup-0.2.0.exe
```

The installer is per-user and installs to:

```text
%LOCALAPPDATA%\Programs\LocalDictation
```

It creates Start Menu shortcuts for the app, settings, and doctor. During setup, the checked setup task prepares the speech model. A separate unchecked task can prepare the optional Ollama cleanup model.

For near-unattended installs, keep the app install separate from setup choices:

```powershell
.\dist\installer\LocalDictationSetup-0.2.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS=""
```

Then prepare the speech model when ready:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" setup bootstrap --stt-only
```

### Developer Install From Source

Open PowerShell in this repo and run:

```powershell
.\scripts\install.ps1
```

The install script creates `.venv` with Python 3.12, upgrades pip, and installs the app in editable mode with developer test dependencies. It can also be invoked by full path from another working directory.

The script does not require activating the virtual environment. To run commands directly, use the environment Python:

```powershell
.\.venv\Scripts\python.exe -m local_dictation doctor
```

If you prefer to activate the environment manually and PowerShell blocks activation scripts, run:

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

`LocalDictation.exe` is the windowed app entry for the tray and settings. `LocalDictationCLI.exe` is the console entry for diagnostics, setup, and test commands.

## Prepare The STT Model

The first model download needs internet. Transcription after the model is cached is local.

For the packaged app:

```powershell
LocalDictationCLI.exe setup bootstrap --stt-only
LocalDictationCLI.exe setup status
```

For the source install:

```powershell
python -m local_dictation setup bootstrap --stt-only
python -m local_dictation setup status
```

The older direct model command still works for source installs:

```powershell
python -m local_dictation download-model
```

Default model: `base.en`.

Speech model choices in Settings:

| Model | Best fit | Tradeoff |
| --- | --- | --- |
| `tiny.en` | Fastest, lightest local transcription | Lower accuracy |
| `base.en` | Default balanced choice | Good first choice for most users |
| `small.en` | Better quality on stronger hardware | Slower and heavier |
| `medium.en` | Highest listed quality option | Heaviest listed option |

For a faster but lower-quality model, choose `tiny.en` in Settings or edit `%APPDATA%\LocalDictation\settings.json` and set:

```json
{
  "stt": {
    "model": "tiny.en"
  }
}
```

For better quality on stronger hardware, choose `small.en` or edit:

```json
{
  "stt": {
    "model": "small.en"
  }
}
```

## Run

```powershell
.\scripts\run.ps1
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
.\.venv\Scripts\python.exe -m local_dictation run --no-tray
```

The tray app also starts a local browser UI at:

```text
http://127.0.0.1:8765/
```

Use the tray menu item `Open Localhost GUI` to open it. The browser UI runs inside the same resident app process as the tray icon. It shows runtime state, last transcript availability, settings path, and whether the core speech model is ready. Turning runtime off in the browser disables dictation listening and hotkey recording, but it does not quit the tray process or disable startup-on-login. If port `8765` is already in use, dictation still runs from the tray and hotkey, but the browser UI is unavailable until the port is free.

You can also open the same browser UI from the command line after the tray app is running:

```powershell
python -m local_dictation gui
```

Packaged app commands:

```powershell
LocalDictation.exe run
LocalDictation.exe settings
LocalDictation.exe gui
LocalDictationCLI.exe doctor
LocalDictationCLI.exe setup bootstrap --stt-only
LocalDictationCLI.exe setup bootstrap --ollama-only
LocalDictationCLI.exe setup status
LocalDictationCLI.exe setup status --with-ollama
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

Ollama cleanup is separate from local speech-to-text. It is disabled by default, and the app uses the raw transcript if Ollama is unavailable.

To prepare the optional cleanup layer, bootstrap can install Ollama through winget and pull the configured local model:

```powershell
python -m local_dictation setup bootstrap --ollama-only
python -m local_dictation setup status --ollama-only
```

For the packaged app, use `LocalDictationCLI.exe` with the same arguments.

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
.\.venv\Scripts\python.exe -m pytest
```

Run setup diagnostics:

```powershell
.\scripts\doctor.ps1
```

Check core speech setup:

```powershell
python -m local_dictation setup status
```

Include optional Ollama cleanup checks only when you are using cleanup:

```powershell
python -m local_dictation setup status --with-ollama
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

## Update

Local Dictation does not self-update. To update an installed copy:

1. Quit Local Dictation from the tray menu.
2. Run the newer installer.
3. Keep the same per-user install location.
4. Launch Local Dictation again from the Start Menu.
5. Open the browser UI and confirm the speech model shows ready.

Settings and logs stay under:

```text
%APPDATA%\LocalDictation
```

If speech-model setup is not ready after the update, run setup from the installed command line:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" setup bootstrap --stt-only
```

## Logs

Logs are written here:

```text
%APPDATA%\LocalDictation\logs\local-dictation.log
```

The tray menu includes `Open Logs`.

## Uninstall And Reset

Uninstall from Windows Settings, or run the uninstaller created by the per-user installer.

To reset app settings, close Local Dictation and rename or delete:

```text
%APPDATA%\LocalDictation\settings.json
```

The app creates default settings on the next run. Logs and downloaded model caches are not reset by deleting this file.

## Troubleshooting

For a packaged install, use `LocalDictationCLI.exe` with the same arguments shown in the `python -m local_dictation ...` examples.

- Hotkey does nothing: run `python -m local_dictation doctor`; another app may own the hotkey. Change the hotkey in Settings.
- No microphone: check Windows privacy settings, default input device, and the `doctor` output.
- First transcription is slow: the speech model may be downloading or loading. Use `tiny.en` for the lightest listed model.
- Setup status fails: run `python -m local_dictation setup bootstrap --stt-only` for the core speech model, then retry `setup status`.
- Cleanup does not run: confirm cleanup is enabled, then run `python -m local_dictation setup status --with-ollama` to check Ollama separately.
- Text does not appear: the target may block focus restoration or simulated input. The final text should remain on the clipboard.
- Elevated target app does not accept input: the app detects likely integrity-level blocking and leaves the final text recoverable instead of blindly inserting into another target.
- `Application Control policy has blocked this file`: Windows security policy blocked a native dependency such as `tokenizers`. Run `python -m local_dictation doctor` from the installed environment, then allow the blocked file/location or use an environment approved by your policy.

## Known Limitations

- First speech model download may require internet.
- Optional Ollama setup may require internet for Ollama and the configured Ollama cleanup model.
- Clipboard fallback attempts to preserve common text, file-drop, and bitmap clipboard formats, but unusual/private formats may not restore.
- Some elevated, protected, remote, game, or virtualized targets may reject simulated input.
- Elevated/protected target support is fail-safe, not privileged UIAccess.
