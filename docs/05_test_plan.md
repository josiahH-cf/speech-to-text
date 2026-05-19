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
  - Ollama winget install and pull commands are tested.

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
2. Run `python -m local_dictation setup bootstrap`.
3. Run `python -m local_dictation run`.
4. Open Notepad.
5. Place cursor in the document.
6. Press `Ctrl+Alt+Space`.
7. Speak a short sentence.
8. Press `Ctrl+Alt+Space` again.
9. Confirm text appears in Notepad.
10. Repeat in a browser text field and a code editor text area.

## Manual Error Tests

- Set an already-used hotkey and verify startup failure is logged.
- Disable or unplug microphone and verify graceful recording failure.
- Enable cleanup without Ollama running and verify raw transcript still inserts.
- Try an elevated target app and verify either insertion succeeds or final text remains on clipboard with a logged warning.
- Build the PyInstaller bundle and run packaged `doctor`.
- Compile the Inno installer and install/uninstall per-user.
