param(
  [switch]$Everything,
  [switch]$KeepModels,
  [switch]$KeepOllama
)

$ErrorActionPreference = "Stop"

if (!$Everything) {
  throw "This script is intentionally destructive. Rerun with -Everything to remove Local Dictation completely."
}

function Write-LocalDictationUninstallProgress {
  param(
    [int]$PercentComplete,
    [string]$Status
  )

  Write-Progress -Activity "Uninstalling Local Dictation" -Status $Status -PercentComplete $PercentComplete
  Write-Host $Status
}

function Remove-LocalDictationPath {
  param([string]$Path)

  if (Test-Path $Path) {
    Remove-Item -Path $Path -Recurse -Force
    Write-Host "Removed: $Path"
  }
}

function Assert-LocalDictationPathRemoved {
  param([string]$Path)

  if (Test-Path $Path) {
    throw "Could not remove: $Path"
  }
}

function Get-LocalDictationModelCachePaths {
  if (![string]::IsNullOrWhiteSpace($env:HUGGINGFACE_HUB_CACHE)) {
    $hub = $env:HUGGINGFACE_HUB_CACHE
  }
  elseif (![string]::IsNullOrWhiteSpace($env:HF_HOME)) {
    $hub = Join-Path $env:HF_HOME "hub"
  }
  elseif (![string]::IsNullOrWhiteSpace($env:XDG_CACHE_HOME)) {
    $hub = Join-Path $env:XDG_CACHE_HOME "huggingface\hub"
  }
  else {
    $hub = Join-Path $HOME ".cache\huggingface\hub"
  }

  $models = @("tiny.en", "base.en", "small.en", "medium.en")
  foreach ($model in $models) {
    $cacheName = "models--Systran--faster-whisper-$model"
    Join-Path $hub $cacheName
    Join-Path (Join-Path $hub ".locks") $cacheName
  }
}

function Get-LocalDictationOllamaModels {
  $models = New-Object System.Collections.Generic.List[string]
  $models.Add("gemma3:1b")
  $settingsPath = Join-Path $env:APPDATA "LocalDictation\settings.json"
  if (Test-Path $settingsPath) {
    try {
      $settings = Get-Content -Raw -Path $settingsPath | ConvertFrom-Json
      if ($settings.cleanup.model) {
        $models.Add([string]$settings.cleanup.model)
      }
    }
    catch {
      Write-Host "Could not read cleanup model from settings; default cleanup model will still be removed if present."
    }
  }
  return $models | Select-Object -Unique
}

function Get-LocalDictationOllamaPaths {
  $paths = New-Object System.Collections.Generic.List[string]
  $paths.Add((Join-Path $HOME ".ollama"))

  if (![string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    $paths.Add((Join-Path $env:LOCALAPPDATA "Ollama"))
    $paths.Add((Join-Path $env:LOCALAPPDATA "Programs\Ollama"))
  }

  if (![string]::IsNullOrWhiteSpace($env:APPDATA)) {
    $paths.Add((Join-Path $env:APPDATA "Ollama"))
  }

  return $paths | Select-Object -Unique
}

function Disable-LocalDictationStartup {
  $cli = Join-Path $env:LOCALAPPDATA "Programs\LocalDictation\LocalDictationCLI.exe"
  if (Test-Path $cli) {
    try {
      & $cli startup disable
      if ($LASTEXITCODE -ne 0) {
        Write-Host "LocalDictationCLI.exe startup disable failed with exit code $LASTEXITCODE; removing startup registry entry directly."
      }
    }
    catch {
      Write-Host "LocalDictationCLI.exe could not disable startup; removing startup registry entry directly."
    }
  }
  Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "LocalDictation" -ErrorAction SilentlyContinue
}

function Uninstall-LocalDictationOllama {
  param([string[]]$Models)

  if ($KeepOllama) {
    Write-Host "Keeping Ollama because -KeepOllama was used."
    return
  }

  Get-Process -Name "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force

  $ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
  if ($ollamaCommand) {
    foreach ($model in $Models) {
      & $ollamaCommand.Source rm $model 2>$null
    }
  }

  $wingetCommand = Get-Command winget -ErrorAction SilentlyContinue
  if ($wingetCommand) {
    & $wingetCommand.Source uninstall --id Ollama.Ollama --exact --silent 2>$null
  }
  else {
    Write-Host "winget was not found; Ollama could not be uninstalled automatically."
  }

  foreach ($path in Get-LocalDictationOllamaPaths) {
    Remove-LocalDictationPath -Path $path
    Assert-LocalDictationPathRemoved -Path $path
  }
}

function Remove-LocalDictationData {
  Remove-LocalDictationPath -Path $appDataDir
  Assert-LocalDictationPathRemoved -Path $appDataDir

  if ($KeepModels) {
    Write-Host "Keeping speech model caches because -KeepModels was used."
    return
  }

  foreach ($path in Get-LocalDictationModelCachePaths) {
    Remove-LocalDictationPath -Path $path
    Assert-LocalDictationPathRemoved -Path $path
  }
}

function Remove-LocalDictationInstallArtifacts {
  $programsDir = [Environment]::GetFolderPath("Programs")
  if (![string]::IsNullOrWhiteSpace($programsDir)) {
    Remove-LocalDictationPath -Path (Join-Path $programsDir "Local Dictation")
  }

  $desktopDir = [Environment]::GetFolderPath("Desktop")
  if (![string]::IsNullOrWhiteSpace($desktopDir)) {
    Remove-LocalDictationPath -Path (Join-Path $desktopDir "Local Dictation.lnk")
  }

  Remove-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{6C9EC15F-627D-4669-B5D9-C986181593B3}_is1" -Recurse -Force -ErrorAction SilentlyContinue
}

$installDir = Join-Path $env:LOCALAPPDATA "Programs\LocalDictation"
$appDataDir = Join-Path $env:APPDATA "LocalDictation"
$ollamaModels = @(Get-LocalDictationOllamaModels)

Write-LocalDictationUninstallProgress -PercentComplete 10 -Status "Stopping Local Dictation if it is running."
Get-Process -Name "LocalDictation", "LocalDictationCLI" -ErrorAction SilentlyContinue | Stop-Process -Force

Write-LocalDictationUninstallProgress -PercentComplete 20 -Status "Disabling startup."
Disable-LocalDictationStartup

Write-LocalDictationUninstallProgress -PercentComplete 55 -Status "Running the Local Dictation uninstaller."
$uninstaller = Get-ChildItem -Path $installDir -Filter "unins*.exe" -File -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
if ($uninstaller) {
  try {
    $process = Start-Process -FilePath $uninstaller.FullName -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") -Wait -PassThru
    if ($process.ExitCode -ne 0) {
      throw "Uninstaller failed with exit code $($process.ExitCode)."
    }
  }
  catch {
    Write-Host "Local Dictation uninstaller could not run; removing installed files directly."
  }
}

Write-LocalDictationUninstallProgress -PercentComplete 75 -Status "Removing remaining installed files."
Remove-LocalDictationPath -Path $installDir
Assert-LocalDictationPathRemoved -Path $installDir
Remove-LocalDictationInstallArtifacts

Write-LocalDictationUninstallProgress -PercentComplete 82 -Status "Removing app data and model caches."
Remove-LocalDictationData

Write-LocalDictationUninstallProgress -PercentComplete 88 -Status "Removing local cleanup pieces."
Uninstall-LocalDictationOllama -Models $ollamaModels

Write-LocalDictationUninstallProgress -PercentComplete 100 -Status "Local Dictation uninstall is complete."
Write-Progress -Activity "Uninstalling Local Dictation" -Completed