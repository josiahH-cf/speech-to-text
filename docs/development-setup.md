# Development Setup

This page is for working on Local Dictation from source. Most end users should start with the root README and the built installer.

## Source Install

Open PowerShell in the repository and run:

```powershell
.\scripts\install.ps1
```

The script creates `.venv` with Python 3.12, upgrades pip, and installs Local Dictation in editable mode with developer dependencies.

Run commands through the virtual environment without activating it:

```powershell
.\.venv\Scripts\python.exe -m local_dictation doctor
.\.venv\Scripts\python.exe -m local_dictation run
```

If you prefer manual activation and PowerShell blocks activation scripts, use a process-scoped policy for the current shell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## Tests

Run the automated tests:

```powershell
.\scripts\test.ps1
```

Pass normal pytest arguments through the wrapper when you want a narrower or more verbose run:

```powershell
.\scripts\test.ps1 tests\test_cli.py -q
```

Run the scripted smoke checklist:

```powershell
.\scripts\smoke-test.ps1
```

Manual smoke test:

1. Run the app.
2. Open Notepad and click in the document.
3. Press `Ctrl+Alt+Space`.
4. Say: `this is a local dictation test`.
5. Press `Ctrl+Alt+Space` again.
6. Confirm text appears in Notepad.
7. Open the tray `Open Localhost GUI` command, or `http://127.0.0.1:8765/` when the default port is free, and confirm the browser UI shows runtime state and settings.
8. Click `Edit Settings`, type into a setting field for more than five seconds, confirm the value is not overwritten, then use `Cancel` or `Save and Resume`.

## Build The Installer

Build the packaged app and installer:

```powershell
.\scripts\build-installer.ps1
```

If Inno Setup is not installed, either install it manually or let the build script install it with winget:

```powershell
.\scripts\build-installer.ps1 -InstallTools
```

Build only the PyInstaller app bundle:

```powershell
.\scripts\build-installer.ps1 -SkipInstaller
```

Outputs:

```text
dist\LocalDictation\LocalDictation.exe
dist\LocalDictation\LocalDictationCLI.exe
dist\installer\LocalDictationSetup-<version>.exe
```

Release builds also write evidence under `dist\release-evidence`.