# Goal Alignment

## Exact User Goal

Build a single self-hosted, self-built, minimalist Windows 11 desktop app for global local dictation.

The user places the cursor in any text target, presses a configurable global hotkey, speaks into the current default Windows microphone, stops recording with the same hotkey or a safety stop, and receives locally generated text inserted back into the original target.

## Minimum Viable Behavior

1. The app runs as a resident Windows tray/background app.
2. A configurable global hotkey toggles recording.
3. Audio is captured from the default Windows input device.
4. Speech is transcribed locally with an open-source model.
5. Optional cleanup/formatting runs through a local model runner.
6. The app attempts to restore focus to the window active when recording began.
7. The final text is inserted into that location using the configured insertion method.
8. The app stays ready for the next dictation.

## Non-Goals For MVP

- No cloud transcription or cloud cleanup.
- No rich UI beyond a tray menu and configuration file.
- No live streaming transcript UI.
- No privileged UIAccess or guaranteed insertion into elevated/protected apps.
- No guarantee of preserving unusual or private clipboard formats.

## Success Criteria

- A user can install the app, run it, dictate into Notepad, and see the text appear in Notepad.
- The same workflow works in common editable browser and editor fields when Windows allows focus restoration and simulated input.
- The app gives clear log messages for microphone, hotkey, transcription, cleanup, focus, insertion, and startup failures.
- Settings can be changed without editing source code.
