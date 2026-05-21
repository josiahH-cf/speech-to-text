# Troubleshooting

## Quick Checks

Run Doctor from the Start Menu or from the installed command line:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" doctor
```

Check speech-model setup:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" setup status
```

Check local cleanup only when you use Ollama:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" setup status --with-ollama
```

## Common Problems

- Hotkey does nothing: another app may own the hotkey. Open Settings, or use `Edit Settings` in the browser UI, choose a different hotkey, then run Doctor.
- No microphone: check Windows privacy settings, the default input device, and Doctor output.
- Quiet microphone input: run Doctor and compare the RMS probe to the configured speech threshold. If quiet speech is below the threshold, open Settings and try the correct input device, a small positive microphone gain, or a lower speech threshold.
- First transcription is slow: the speech model may be downloading or loading. Use `tiny.en` for the lightest listed model.
- Setup status fails: run `setup bootstrap --stt-only`, then retry `setup status`.
- Cleanup does not run: confirm cleanup is enabled, then run `setup status --with-ollama`.
- Text does not appear: the target app may block simulated input. The final text should remain recoverable through the clipboard fallback.
- Text only copies to the clipboard: Local Dictation probably could not restore focus, type into the target, or inject into an elevated/protected app. The tray and browser UI show the last outcome; open logs for the detailed branch.
- Elevated target app does not accept input: run Local Dictation at the same integrity level as the target, or paste from the clipboard fallback.
- Browser UI does not open or shows a different app (e.g. `{"apiVersion": "AnkiConnect v.6"}`): port `8765` is in use by another process such as AnkiConnect. Local Dictation automatically tries nearby loopback ports, and tray and hotkey dictation can still work. Use `Open Localhost GUI` or `LocalDictationCLI.exe gui` to open the active URL, then check logs or run Doctor if no recovered URL responds.
- Browser settings fields keep resetting while you type: use `Edit Settings` first. Edit mode pauses dictation listening and prevents automatic status refresh from replacing unsaved form input.

## Logs And Settings

Logs are written here:

```text
%APPDATA%\LocalDictation\logs\local-dictation.log
```

Settings are written here:

```text
%APPDATA%\LocalDictation\settings.json
```

The tray menu includes `Open Logs` and `Open Settings Folder`. The settings window also includes `Open Settings Folder`.

The browser UI prefers `http://127.0.0.1:8765/` while the tray app is running and shows the current state, last dictation result, settings path, and core setup status. If that port is busy, the app logs the recovered loopback URL and the tray/CLI GUI commands open it. Use `Edit Settings` before changing browser settings so runtime listening pauses and form input is not overwritten by refresh.

## Reset Or Remove Data

Preview Local Dictation cleanup targets:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" cleanup-data --all --dry-run
```

Remove settings, logs, and known speech-model caches:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" cleanup-data --all --yes
```

Remove everything, including installed files and startup state, from the repository helper:

```powershell
.\scripts\uninstall-user.ps1 -Everything
```

## Security Policy Blocks

If Windows reports `Application Control policy has blocked this file`, a native dependency such as `tokenizers` may be blocked. Run Doctor from the installed environment, then allow the blocked file/location or use an environment approved by your policy.