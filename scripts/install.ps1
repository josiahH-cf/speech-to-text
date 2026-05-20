$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"
Set-LocalDictationRepoRoot
Assert-LocalDictationPython312

py -3.12 -m venv .venv
$python = Get-LocalDictationVenvPython
& $python -m pip install --upgrade pip
& $python -m pip install -e ".[dev]"

Write-Host "Installed Local Dictation into .venv"
Write-Host "Run: .\.venv\Scripts\python.exe -m local_dictation doctor"
