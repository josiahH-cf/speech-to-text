# Local Dictation

Local Dictation is a Windows local dictation app. It lives in the system tray, listens for a hotkey, records from your default microphone, transcribes locally with `faster-whisper`, and types the final text into the app you were using.

Default hotkey: `Ctrl+Alt+Space`.

## Install Everything

Use this when you want the normal setup: app installed, speech model prepared, startup enabled, and Local Dictation launched when setup finishes.

```powershell
.\scripts\install-user.ps1
```

The script builds the installer automatically if one does not exist under `dist\installer\`, then installs the app, prepares the speech model, enables startup, launches Local Dictation, and checks the local browser UI. If the default browser UI port is busy, the app recovers on a nearby loopback port and the script prints the working URL. Add `-InstallTools` if Inno Setup is not installed. To use an installer you already have (for example, downloaded from GitHub Releases), pass `-InstallerPath`:

```powershell
.\scripts\install-user.ps1 -InstallerPath "C:\path\to\LocalDictationSetup-0.2.0.exe"
```

After install:

1. Put your cursor in a text field.
2. Press `Ctrl+Alt+Space`.
3. Speak.
4. Press `Ctrl+Alt+Space` again.
5. Wait for the text to appear.

Local Dictation will start again when you sign in to Windows. To install without startup, use:

```powershell
.\scripts\install-user.ps1 -NoStartup
```

## Install Without Preparing The Speech Model

Use this if you want the app installed now but want to download or prepare the speech model later.

```powershell
.\scripts\install-user.ps1 -SkipSpeechModel
```

This keeps the app intact, but usable dictation still requires a speech model. Prepare it later from the installed command line:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" setup bootstrap --stt-only
```

## Add Local Cleanup With Ollama

Local cleanup can add punctuation and formatting through a local Ollama model. It is not required for dictation, but it is supported as a one-command setup choice.

```powershell
.\scripts\install-user.ps1 -WithOllama
```

This can take longer. It may install Ollama through `winget`, pull the configured local cleanup model, and turn cleanup on.

## Uninstall Everything

Use this when you want Local Dictation removed completely.

```powershell
.\scripts\uninstall-user.ps1 -Everything
```

This removes the installed app, shortcuts, startup entry, settings, logs, known Local Dictation speech-model caches, and local cleanup pieces. If you want to keep shared model downloads or Ollama for other tools, use `-KeepModels` or `-KeepOllama`.

## Launch And Configure

Local Dictation starts automatically after the normal install. You can also launch it from the Start Menu shortcut named `Local Dictation`.

Right-click the tray icon for:

- `Settings`
- `Open Settings Folder`
- `Open Localhost GUI`
- `Reload Settings`
- `Open Logs`
- `Run Doctor`
- `Quit`

The local browser UI is available while the tray app is running. The preferred URL is:

```text
http://127.0.0.1:8765/
```

If that port is already in use, Local Dictation automatically tries nearby loopback ports. Use the tray menu or the `gui` command to open the active recovered URL.

Use `Edit Settings` in the browser UI before changing settings there. Edit mode pauses dictation listening while the form is open, keeps the automatic status refresh from overwriting your typing, then `Save and Resume` applies the new settings and restores listening if it was on before. `Cancel` exits edit mode and discards unsaved form edits.

Settings and logs live under `%APPDATA%\LocalDictation`:

- Settings file: `%APPDATA%\LocalDictation\settings.json`
- Logs folder: `%APPDATA%\LocalDictation\logs`

You can open settings from the tray, from the browser UI, or from the installed command line:

```powershell
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" settings
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" gui
& "$env:LOCALAPPDATA\Programs\LocalDictation\LocalDictationCLI.exe" doctor
```

In Settings or the browser UI, most people only need these choices:

- Hotkey: default is `Ctrl+Alt+Space`.
- Input device: `default` uses the Windows default microphone; Doctor lists numeric input device IDs.
- Microphone gain: use a small positive dB value if quiet speech stays below the speech threshold.
- Recording cue: default is `off`; choose one of the three muted built-in tones for microphone start and stop feedback.
- Speech threshold and silence seconds: adjust these only when silence stop starts or stops too aggressively.
- Speech model: `base.en` is the default and best first choice.
- Startup: enabled by the normal install script unless you used `-NoStartup`.
- Cleanup: use Ollama only if you want local punctuation/formatting cleanup.

Speech model guide:

| Model | Best fit | Tradeoff |
| --- | --- | --- |
| `tiny.en` | Older or slower machines | Fastest, lower accuracy |
| `base.en` | Most users | Default balanced choice |
| `small.en` | Stronger machines | Better accuracy, slower |
| `medium.en` | Highest listed quality | Heaviest and slowest listed option |

The app creates settings automatically, reloads safe setting changes, reports the last dictation outcome in the tray and browser UI, and falls back to raw transcription if cleanup is unavailable.

## If The Browser UI Does Not Open

The tray app prefers `http://127.0.0.1:8765/` for the browser UI. If that port is already busy, Local Dictation automatically recovers on a nearby loopback port and dictation can still work from the tray and hotkey.

Try this:

1. Right-click the tray icon and choose `Open Localhost GUI`.
2. Or run `LocalDictationCLI.exe gui` from the installed command line.
3. If it still does not open, run `Doctor` from the Start Menu and check the logs.

## Advanced Docs

- [docs/development-setup.md](docs/development-setup.md) for source installs, tests, and builds.
- [docs/command-reference.md](docs/command-reference.md) for CLI commands.
- [docs/troubleshooting.md](docs/troubleshooting.md) for logs, diagnostics, reset, and security-policy issues.
- [docs/09_enterprise_security_review.md](docs/09_enterprise_security_review.md) for managed Windows review.
- [docs/10_release_and_supply_chain.md](docs/10_release_and_supply_chain.md) for release and supply-chain notes.