$ErrorActionPreference = "Stop"

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

Write-Host "Installed Local Dictation into .venv"
Write-Host "Run: .\.venv\Scripts\python.exe -m local_dictation doctor"
