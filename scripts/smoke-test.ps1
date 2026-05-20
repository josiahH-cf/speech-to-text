$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"
Set-LocalDictationRepoRoot
$python = Get-LocalDictationVenvPython

& $python -m local_dictation doctor
& $python -m local_dictation setup status
if ($LASTEXITCODE -ne 0) {
  Write-Host "Speech model setup is not complete yet. Run setup bootstrap --stt-only when you are ready to prepare dictation."
}

Write-Host ""
Write-Host "Local browser UI check:"
try {
  $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8765/" -TimeoutSec 2 -ErrorAction Stop
  if ($response.StatusCode -eq 200) {
    Write-Host "OK Local browser UI is responding at http://127.0.0.1:8765/."
  }
  else {
    Write-Host "WARN Local browser UI returned HTTP $($response.StatusCode)."
  }
}
catch {
  Write-Host "INFO Local browser UI is not responding. Start the tray app, then open http://127.0.0.1:8765/ or use the tray menu."
}

Write-Host ""
Write-Host "Manual end-to-end smoke test:"
Write-Host "1. Run: .\.venv\Scripts\python.exe -m local_dictation run"
Write-Host "2. Open Notepad and click in the document."
Write-Host "3. Press Ctrl+Alt+Space."
Write-Host "4. Say: this is a local dictation test"
Write-Host "5. Press Ctrl+Alt+Space again."
Write-Host "6. Confirm the text appears in Notepad."
Write-Host "7. Open http://127.0.0.1:8765/ and confirm the browser UI shows runtime state and settings."
