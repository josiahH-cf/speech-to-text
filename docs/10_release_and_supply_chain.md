# Release and Supply Chain Notes

This document describes the build inputs and release evidence that make Local Dictation easier to review. It is intentionally small: it records what was built and how to verify it without adding mandatory release infrastructure.

## Build Inputs

- Python: 3.12, verified by `scripts/common.ps1`.
- Project dependencies: declared in `pyproject.toml`.
- Packager: PyInstaller through `packaging/LocalDictation.spec`.
- Installer: Inno Setup through `packaging/LocalDictation.iss`.
- Main packaged artifacts:
  - `dist\LocalDictation\LocalDictation.exe`
  - `dist\LocalDictation\LocalDictationCLI.exe`
  - `dist\installer\LocalDictationSetup-0.2.0.exe`

## Build Command

Standard local build:

```powershell
.\scripts\build-installer.ps1
```

Build only the PyInstaller bundle:

```powershell
.\scripts\build-installer.ps1 -SkipInstaller
```

Optional signed build when an Authenticode certificate is available:

```powershell
.\scripts\build-installer.ps1 -CodeSigningCertThumbprint "<thumbprint>" -TimestampUrl "http://timestamp.digicert.com"
```

If no certificate thumbprint is supplied, the build still succeeds and emits a warning that artifacts are unsigned.

## Release Evidence

The build writes compact evidence under:

```text
dist\release-evidence
```

Expected files:

- `CHECKSUMS.sha256`: SHA-256 hashes for generated artifacts that exist.
- `SIGNATURES.txt`: Authenticode signature status and signer subject for each artifact.
- `DIRECT-DEPENDENCIES.txt`: direct runtime dependencies from `pyproject.toml`.
- `BUILD-PROVENANCE.txt`: timestamp, Git commit when available, Python version, PyInstaller version, UPX state, and whether signing was requested.

## Signing

Signing is performed after artifacts are built with `signtool.exe` when `-CodeSigningCertThumbprint` is provided. The script looks for `signtool.exe` on PATH and in common Windows SDK locations.

Verify signatures manually with:

```powershell
Get-AuthenticodeSignature .\dist\LocalDictation\LocalDictation.exe
Get-AuthenticodeSignature .\dist\LocalDictation\LocalDictationCLI.exe
Get-AuthenticodeSignature .\dist\installer\LocalDictationSetup-0.2.0.exe
```

## Dependency and Model Notes

Direct dependencies are declared in `pyproject.toml`. The most review-relevant packages are:

- `faster-whisper`: local speech-to-text model loading and transcription.
- `sounddevice`: microphone capture.
- `pywin32`: Windows hotkey, window, clipboard, and registry APIs.
- `pystray` and `Pillow`: tray UI.
- `pyinstaller`: build-time executable packaging.

`faster-whisper` may use its normal model cache when model files are not already present and `local_files_only` is false. Optional Ollama setup can install Ollama through winget and pull the configured cleanup model. These setup flows are documented so reviewers can distinguish first-run or setup-time downloads from ordinary runtime dictation.

## Review Boundaries

This release process avoids mandatory SBOM tooling, lockfile migration, installer signing directives that break local builds, or policy profiles that change runtime behavior. Those can be added later as release-engineering improvements, but they are not required for the minimal audit-readiness slice.