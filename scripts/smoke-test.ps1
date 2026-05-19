$ErrorActionPreference = "Stop"

.\.venv\Scripts\python.exe -m local_dictation doctor
.\.venv\Scripts\python.exe -m local_dictation setup status
if ($LASTEXITCODE -ne 0) {
  Write-Host "Setup status is not complete yet. Run setup bootstrap when you are ready to prepare Ollama."
}

Write-Host ""
Write-Host "Manual end-to-end smoke test:"
Write-Host "1. Run: .\.venv\Scripts\python.exe -m local_dictation run"
Write-Host "2. Open Notepad and click in the document."
Write-Host "3. Press Ctrl+Alt+Space."
Write-Host "4. Say: this is a local dictation test"
Write-Host "5. Press Ctrl+Alt+Space again."
Write-Host "6. Confirm the text appears in Notepad."
