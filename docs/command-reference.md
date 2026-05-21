# Command Reference

For packaged installs, run commands from:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" <command>
```

For source installs, use:

```powershell
python -m local_dictation <command>
```

## App Commands

```powershell
LocalDictation.exe run
LocalDictation.exe settings
LocalDictation.exe gui
```

- `run` starts the tray app.
- `settings` opens the Tkinter settings window.
- `gui` opens the active localhost browser UI after the tray app is running, including a recovered URL if the default port was busy. Use the browser UI's `Edit Settings` control before changing settings so dictation listening pauses and form fields are not overwritten by status refresh.

## CLI Commands

```powershell
LocalDictationCLI.exe doctor
LocalDictationCLI.exe setup bootstrap --stt-only
LocalDictationCLI.exe setup bootstrap --ollama-only
LocalDictationCLI.exe setup bootstrap --ollama-only --enable-cleanup
LocalDictationCLI.exe setup status
LocalDictationCLI.exe setup status --with-ollama
LocalDictationCLI.exe startup enable
LocalDictationCLI.exe startup disable
LocalDictationCLI.exe startup status
LocalDictationCLI.exe download-model
LocalDictationCLI.exe transcribe-file sample.wav
LocalDictationCLI.exe insert-test --text "Local Dictation insert test"
LocalDictationCLI.exe cleanup-data --all --yes
```

Use `cleanup-data --dry-run --all` to preview app-data and known speech-model cache removal before deleting anything.