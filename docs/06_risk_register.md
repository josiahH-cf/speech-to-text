# Risk Register

## R1: Hotkey Conflicts

Risk: The configured hotkey is already registered by another process.

Mitigation:
- Use `RegisterHotKey` return status and log `GetLastError`.
- Keep hotkey configurable.
- Document changing `settings.json`.

## R2: Microphone Access Failure

Risk: No default microphone exists, privacy settings block access, or another app has exclusive control.

Mitigation:
- `doctor` checks default input.
- Runtime catches capture errors and stays resident.
- Logs include the sounddevice error.

## R3: Slow Or Missing STT Model

Risk: First run requires model download, or CPU transcription is slow on large models.

Mitigation:
- Default to `base.en` and CPU `int8`.
- Provide `download-model` command.
- Make model configurable.
- Document `tiny.en` for speed and larger models for quality.

## R4: Ollama Unavailable

Risk: Cleanup is enabled but Ollama is not installed, not running, or model is missing.

Mitigation:
- Cleanup disabled by default.
- Cleanup failure falls back to raw transcript.
- `doctor` checks endpoint only when cleanup is enabled.

## R5: Focus Restore Denied

Risk: Windows refuses `SetForegroundWindow`.

Mitigation:
- Capture target window before recording.
- Attempt restore with timeout.
- If restore fails, leave final text on clipboard instead of pasting into an unknown target.

## R6: Clipboard Side Effects

Risk: Clipboard fallback replaces existing non-text clipboard content.

Mitigation:
- Prefer direct Unicode typing first.
- Snapshot and restore common clipboard formats when fallback is used.
- Document that unusual/private formats may still be lost.

## R7: Elevated Or Protected Targets

Risk: `SendInput` typing or paste may be blocked by integrity level or target app behavior.

Mitigation:
- Log insertion failure.
- Leave final text on clipboard.
- Document running the app at matching integrity only if the user accepts the security tradeoff.

## R9: Installer Tooling Missing

Risk: PyInstaller or Inno Setup is not installed on the build machine.

Mitigation:
- Pin PyInstaller in the build dependency group.
- Build script installs Python build dependencies automatically.
- Build script can install Inno Setup through winget with `-InstallTools`.

## R10: Ollama Auto-Install Fails

Risk: winget is unavailable, policy blocks install, or Ollama model pull fails.

Mitigation:
- Setup status records each step.
- Cleanup remains optional and fails open to raw transcript.
- User can rerun `setup bootstrap` after fixing the environment.

## R8: Native Dependency Blocked By Windows Policy

Risk: Windows Application Control or antivirus policy blocks a native dependency such as `tokenizers`, causing `faster-whisper` import or model loading to fail.

Mitigation:
- Doctor imports runtime modules instead of only checking package presence.
- Transcription errors include the underlying import failure.
- Troubleshooting docs tell the user to allow the blocked dependency or install into an approved environment.
