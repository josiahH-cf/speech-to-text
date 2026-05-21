# Test Plan

## Automated Tests

- Configuration:
  - Default settings contain all required sections.
  - Missing settings are filled from defaults.
  - Existing unknown settings are preserved.
- Hotkey:
  - `ctrl+alt+space` parses to Control, Alt, and Space.
  - Invalid hotkeys raise a clear validation error.
  - `f12` is rejected.
- Cleanup:
  - Disabled cleanup returns raw text unchanged.
  - Prompt construction is deterministic.
  - Ollama failure returns raw text and does not raise.
- Startup:
  - Startup command includes the current Python executable, module invocation, and run command.
- Insertion:
  - Direct typing UTF-16 unit generation is tested.
  - Target integrity classification is tested.
  - Clipboard snapshot helper behavior is tested without touching Windows clipboard APIs.
- Recording:
  - Silence stop rules are tested.
- Setup:
  - Core STT status can pass without Ollama installed or reachable.
  - Optional Ollama status can be requested explicitly.
  - Ollama winget install and pull commands are tested.
- Local browser UI:
  - Default localhost constants point to `http://127.0.0.1:8765/`.
  - Occupied configured ports recover to a nearby loopback port and expose the active URL.
  - State endpoint reports runtime state, hotkey, STT model, cleanup settings, settings path, and core setup readiness.
  - Setup endpoint reports core speech-model readiness without checking optional Ollama.
  - Settings endpoint validates hotkeys, updates model settings, and forces settings reload.
  - Edit mode endpoint pauses runtime while idle, rejects busy recording or processing states, and resumes only when the runtime was enabled before edit mode.
  - Edit-mode settings save validates and persists settings, reloads while paused, exits edit mode, and preserves edit mode on validation failure.
  - Browser page wiring suppresses full form-refresh overwrites while edit mode is active.
  - Mutation endpoints reject missing or invalid local tokens.
  - Runtime and recording endpoints return a busy response instead of interrupting processing.
  - CLI `gui` command opens the existing tray-hosted URL without starting another server.
- Runtime lifecycle:
  - Process start and stop remain idempotent.
  - Runtime enable and disable only control dictation listening.
  - Runtime disable is rejected while recording or processing.

## Doctor Checks

`python -m local_dictation doctor` reports:

- Python version.
- Package import availability.
- Settings file path.
- Log directory path.
- Hotkey parse status.
- Default microphone status.
- STT model setting.
- Ollama reachability when cleanup is enabled.
- Startup registration status.
- Setup/bootstrap status.

## Manual End-To-End Smoke Test

1. Install dependencies.
2. Run `python -m local_dictation setup bootstrap --stt-only`.
3. Run `python -m local_dictation run`.
4. Open Notepad.
5. Place cursor in the document.
6. Press `Ctrl+Alt+Space`.
7. Speak a short sentence.
8. Press `Ctrl+Alt+Space` again.
9. Confirm text appears in Notepad.
10. Repeat in a browser text field and a code editor text area.
11. Open the local browser UI from the tray menu.
12. Confirm the browser UI shows the current runtime state, hotkey, STT model, cleanup settings, and core speech-model readiness.
13. Disable runtime in the browser UI and verify the hotkey no longer starts recording.
14. Re-enable runtime in the browser UI and verify hotkey dictation works again.
15. Enter browser Edit mode, type into settings fields for more than five seconds, verify values are not overwritten, then save and confirm runtime resumes when it was previously enabled.

## Manual Error Tests

- Set an already-used hotkey and verify startup failure is logged.
- Disable or unplug microphone and verify graceful recording failure.
- Enable cleanup without Ollama running and verify raw transcript still inserts.
- Try an elevated target app and verify either insertion succeeds or final text remains on clipboard with a logged warning.
- Build the PyInstaller bundle and run packaged `doctor`.
- Launch the tray app and verify the reported localhost UI URL is available only while the tray process is running.
- Occupy port `8765` before launching the tray app and verify dictation still runs while the browser UI recovers on a nearby loopback port and logs the recovered URL.
- Compile the Inno installer and install/uninstall per-user.
