$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"
Set-LocalDictationRepoRoot
$python = Get-LocalDictationVenvPython

& $python -m local_dictation doctor
& $python -m local_dictation setup status
if ($LASTEXITCODE -ne 0) {
  Write-Host "Speech model setup is not complete yet. Run setup bootstrap --stt-only when you are ready to prepare dictation."
}

function Get-LocalDictationLocalGuiUrls {
  $urls = @()
  $stateFile = Join-Path $env:APPDATA "LocalDictation\local-gui.json"
  if (Test-Path $stateFile) {
    try {
      $state = Get-Content $stateFile -Raw | ConvertFrom-Json
      if ($null -ne $state.url -and ![string]::IsNullOrWhiteSpace([string]$state.url)) {
        $urls += [string]$state.url
      }
    }
    catch { }
  }

  $port = 8765
  $settingsFile = Join-Path $env:APPDATA "LocalDictation\settings.json"
  if (Test-Path $settingsFile) {
    try {
      $settings = Get-Content $settingsFile -Raw | ConvertFrom-Json
      if ($null -ne $settings.gui -and $null -ne $settings.gui.port) {
        $port = $settings.gui.port
      }
    }
    catch { }
  }

  $urls += "http://127.0.0.1:$port/"
  return $urls | Where-Object { ![string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
}

Write-Host ""
Write-Host "Local browser UI check:"
$localGuiResponded = $false
foreach ($url in Get-LocalDictationLocalGuiUrls) {
  $normalizedUrl = if ($url.EndsWith("/")) { $url } else { "$url/" }
  $baseUrl = $normalizedUrl.TrimEnd('/')
  $pingUrl = "$baseUrl/api/ping"
  try {
    $response = Invoke-RestMethod -Uri $pingUrl -TimeoutSec 2 -ErrorAction Stop
    if ($response.app -eq "local-dictation") {
      Write-Host "OK Local browser UI is responding at $normalizedUrl."
      $localGuiResponded = $true
      break
    }
  }
  catch {
  }

  $stateUrl = "$baseUrl/api/state"
  try {
    $response = Invoke-RestMethod -Uri $stateUrl -TimeoutSec 2 -ErrorAction Stop
    if ($null -ne $response.sttModel -and $null -ne $response.settingsPath -and ([string]$response.settingsPath).Contains("LocalDictation")) {
      Write-Host "OK Local browser UI is responding at $normalizedUrl."
      $localGuiResponded = $true
      break
    }
  }
  catch {
    continue
  }
}
if (!$localGuiResponded) {
  Write-Host "INFO Local browser UI is not responding. Start the tray app, then use the tray menu or python -m local_dictation gui."
}

Write-Host ""
Write-Host "Manual end-to-end smoke test:"
Write-Host "1. Run: .\.venv\Scripts\python.exe -m local_dictation run"
Write-Host "2. Open Notepad and click in the document."
Write-Host "3. Press Ctrl+Alt+Space."
Write-Host "4. Say: this is a local dictation test"
Write-Host "5. Press Ctrl+Alt+Space again."
Write-Host "6. Confirm the text appears in Notepad."
Write-Host "7. Open the local browser UI from the tray menu and confirm it shows runtime state and settings."
