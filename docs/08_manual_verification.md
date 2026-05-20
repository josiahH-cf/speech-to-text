# Manual Verification

Record results here before marking v0.2 complete.

## Environment

- Windows version: Windows 11 local verification host
- App version: 0.2.0
- Installer path: `dist\installer\LocalDictationSetup-0.2.0.exe`
- STT model: `base.en`
- Ollama model: `gemma3:1b`

## Installer

- [x] `scripts/build-installer.ps1` builds `dist\LocalDictation`.
- [x] `scripts/build-installer.ps1` builds `dist\installer\LocalDictationSetup-0.2.0.exe`.
- [x] Installer completes as a per-user install.
- [x] Start Menu shortcuts point to app, settings, and doctor commands.
- [x] Installed startup command writes and removes the current-user startup entry.
- [x] Uninstall removes app files.
- [x] Installed app launches without immediately exiting.

Notes:
- Silent install with optional tasks disabled installed to `%LOCALAPPDATA%\Programs\LocalDictation`.
- Installed `LocalDictationCLI.exe doctor` exited `0` after the console/GUI executable split.
- Installed `LocalDictation.exe run` started successfully and was stopped after a resident-app launch check.
- Silent uninstall removed the install directory.
- Follow-up review rebuilt and reinstalled the per-user app after fixing packaged diagnostic launch paths and deferred hotkey re-registration.
- Final review left the per-user app installed at `%LOCALAPPDATA%\Programs\LocalDictation`.
- Reinstall briefly created an Inno `is-*.tmp` file that cleared after installer finalization.
- Independent verification on 2026-05-19 rebuilt the PyInstaller bundle and Inno installer after repairing settings validation and packaged hotkey message handling.
- Silent reinstall with optional tasks disabled installed to `%LOCALAPPDATA%\Programs\LocalDictation` and produced `LocalDictation.exe` and `LocalDictationCLI.exe` launchers.
- Installed `LocalDictationCLI.exe doctor` and `LocalDictationCLI.exe setup status` exited `0` outside an activated Python environment.
- Start Menu shortcut targets were verified: app uses `LocalDictation.exe run`, settings uses `LocalDictation.exe settings`, and doctor uses `LocalDictationCLI.exe doctor`.
- `LocalDictation.exe settings` launched a resident settings process and was then stopped cleanly.
- Installed `LocalDictationCLI.exe startup enable` wrote the HKCU `LocalDictation` Run entry pointing to installed `LocalDictation.exe run`; `startup disable` removed it.
- 2026-05-20 verification rebuilt `dist\LocalDictation` and `dist\installer\LocalDictationSetup-0.2.0.exe` after script cwd hardening.
- `scripts\build-installer.ps1 -SkipInstaller` succeeded when invoked by full path from `$env:TEMP` and rebuilt `dist\LocalDictation`.
- Silent installer validation with `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS=""` exited `0` and installed both packaged launchers to `%LOCALAPPDATA%\Programs\LocalDictation`.
- Installed `LocalDictationCLI.exe doctor` and `LocalDictationCLI.exe setup status` exited `0` after the silent install.
- Installed `LocalDictationCLI.exe startup enable` wrote the HKCU Run command for installed `LocalDictation.exe run`; `startup disable` removed it.
- Installed `LocalDictation.exe run` stayed resident for a bounded launch check and logged successful hotkey registration before being stopped.

## Dictation Targets

- [ ] Notepad: hotkey starts/stops and text appears.
- [ ] Browser text field: hotkey starts/stops and text appears.
- [ ] Editor text field: hotkey starts/stops and text appears.
- [x] Installed-app Windows text target: hotkey starts, captures default microphone, silence stops, transcription inserts text.
- [x] Silence auto-stop finishes a recording after speech and silence.
- [ ] Clipboard content remains unchanged after direct typing.
- [ ] Clipboard fallback leaves recoverable text if direct typing fails.
- [ ] Elevated/protected target fails safe without inserting into the wrong place.

Notes:
- Installed `LocalDictationCLI.exe insert-test --text "Local Dictation insert test"` inserted text into a focused Windows Forms text box with exit code `0`.
- Installed `LocalDictation.exe run` registered `ctrl+alt+space`, captured the default microphone, transcribed the spoken phrase "this is a local dictation smoke test", and inserted `This is a local dictation smoke test.` with direct Unicode typing.
- Log evidence for the installed smoke test: hotkey registered, recording started, silence requested stop after 6.83 seconds, `base.en` loaded, transcription completed with 37 characters, and direct Unicode typing inserted the text.
- A Notepad automation attempt did not produce enough clipboard/log evidence to mark the dedicated Notepad target complete. Browser, editor, clipboard preservation, clipboard fallback, and elevated/protected-target checks remain manual target coverage gaps.

## Setup

- [x] `LocalDictationCLI.exe setup bootstrap` prepares the configured STT model.
- [x] Ollama auto-install path installs or detects Ollama through winget.
- [x] `ollama pull` prepares the configured cleanup model.
- [x] `LocalDictationCLI.exe setup status` reports accurate setup state.
- [x] `LocalDictationCLI.exe transcribe-file` loads `base.en` and exits `0` on a local WAV smoke file.
- [x] Cleanup enabled with unreachable Ollama endpoint fails open to raw transcript.

Notes:
- Bootstrap installed/detected Ollama through winget and prepared the configured cleanup model.
- `LocalDictationCLI.exe setup status` reports STT model ready, winget available, Ollama executable available, and Ollama API reachable.
- `LocalDictationCLI.exe transcribe-file` loaded `base.en` and exited `0` against a generated silent WAV smoke file.
- Installed `LocalDictationCLI.exe setup bootstrap` completed successfully during independent verification with the configured STT model ready and Ollama reachable.
- With cleanup temporarily enabled and pointed at an unreachable local endpoint with a 1-second timeout, installed dictation still inserted the raw transcript and logged `Ollama cleanup failed; using raw transcript`; settings were restored afterward.
- 2026-05-20 source `scripts\install.ps1`, `scripts\doctor.ps1`, and `scripts\smoke-test.ps1` exited `0` when invoked by full path from `$env:TEMP`; no `.venv` was created in the caller's temp directory.
- 2026-05-20 packaged `LocalDictationCLI.exe doctor` and `setup status` exited `0`; setup status reported STT model ready, winget available, Ollama executable available, and Ollama API reachable.
- End-to-end live dictation into dedicated Notepad, browser, and editor fields still requires interactive target testing.
