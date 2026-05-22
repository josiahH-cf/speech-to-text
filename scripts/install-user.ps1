param(
  [string]$InstallerPath = "",
  [switch]$InstallTools,
  [switch]$SkipSpeechModel,
  [switch]$WithOllama,
  [switch]$NoStartup,
  [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"
Set-LocalDictationRepoRoot

if ($SkipSpeechModel -and $WithOllama) {
  throw "Choose either -SkipSpeechModel or -WithOllama. Local cleanup setup is useful after the speech model is prepared."
}

function Write-LocalDictationInstallProgress {
  param(
    [int]$PercentComplete,
    [string]$Status
  )

  Write-Progress -Activity "Installing Local Dictation" -Status $Status -PercentComplete $PercentComplete
  Write-Host $Status
}

function Resolve-LocalDictationInstaller {
  param([string]$Path)

  if (![string]::IsNullOrWhiteSpace($Path)) {
    if (!(Test-Path -LiteralPath $Path)) {
      throw "Installer not found at '$Path'. Check the path or omit -InstallerPath to auto-build."
    }
    $resolved = Resolve-Path -Path $Path -ErrorAction Stop
    return $resolved.Path
  }

  $installer = Get-ChildItem -Path "dist\installer" -Filter "LocalDictationSetup-*.exe" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if ($installer) {
    return $installer.FullName
  }

  throw "Installer was not found. Pass -InstallerPath or place LocalDictationSetup-*.exe under dist\installer."
}

function Invoke-LocalDictationCli {
  param([string[]]$Arguments)

  $cli = Join-Path $env:LOCALAPPDATA "Programs\LocalDictation\LocalDictationCLI.exe"
  if (!(Test-Path $cli)) {
    throw "LocalDictationCLI.exe was not found at $cli. The install may not have completed."
  }

  & $cli @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "LocalDictationCLI.exe $($Arguments -join ' ') failed with exit code $LASTEXITCODE."
  }
}

function Start-LocalDictationApp {
  $app = Join-Path $env:LOCALAPPDATA "Programs\LocalDictation\LocalDictation.exe"
  if (!(Test-Path $app)) {
    throw "LocalDictation.exe was not found at $app. The install may not have completed."
  }

  Start-Process -FilePath $app -ArgumentList "run"
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

function Test-LocalDictationLocalGui {
  param(
    [int]$Attempts = 60,
    [int]$DelayMilliseconds = 500
  )

  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    foreach ($url in Get-LocalDictationLocalGuiUrls) {
      $normalizedUrl = if ($url.EndsWith("/")) { $url } else { "$url/" }
      $baseUrl = $normalizedUrl.TrimEnd('/')
      $pingUrl = "$baseUrl/api/ping"
      try {
        $response = Invoke-RestMethod -Uri $pingUrl -TimeoutSec 2 -ErrorAction Stop
        if ($response.app -eq "local-dictation") {
          return $normalizedUrl
        }
      }
      catch { }

      $stateUrl = "$baseUrl/api/state"
      try {
        $response = Invoke-RestMethod -Uri $stateUrl -TimeoutSec 2 -ErrorAction Stop
        if ($null -ne $response.sttModel -and $null -ne $response.settingsPath -and ([string]$response.settingsPath).Contains("LocalDictation")) {
          return $normalizedUrl
        }
      }
      catch { }
    }

    if ($attempt -lt $Attempts) {
      Start-Sleep -Milliseconds $DelayMilliseconds
    }
  }

  return $null
}

if ([string]::IsNullOrWhiteSpace($InstallerPath)) {
  $existing = Get-ChildItem -Path "dist\installer" -Filter "LocalDictationSetup-*.exe" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (!$existing) {
    Write-Host "No installer found under dist\installer. Building now..."
    $buildArgs = @{}
    if ($InstallTools) { $buildArgs["InstallTools"] = $true }
    & "$PSScriptRoot\build-installer.ps1" @buildArgs
  }
}

$installer = Resolve-LocalDictationInstaller -Path $InstallerPath
$tasks = @()
if (!$NoStartup) {
  $tasks += "startup"
}
$taskArgument = "/TASKS=`"$($tasks -join ',')`""
$installerArguments = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", $taskArgument)

Write-LocalDictationInstallProgress -PercentComplete 10 -Status "Using installer: $installer"
Write-LocalDictationInstallProgress -PercentComplete 20 -Status "Stopping Local Dictation if it is running."
Get-Process -Name "LocalDictation", "LocalDictationCLI" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-LocalDictationInstallProgress -PercentComplete 25 -Status "Installing Local Dictation."
$process = Start-Process -FilePath $installer -ArgumentList $installerArguments -Wait -PassThru
if ($process.ExitCode -ne 0) {
  throw "Installer failed with exit code $($process.ExitCode)."
}

if (!$SkipSpeechModel) {
  Write-LocalDictationInstallProgress -PercentComplete 50 -Status "Preparing the local speech model. This can take a few minutes the first time."
  Invoke-LocalDictationCli -Arguments @("setup", "bootstrap", "--stt-only")
}
else {
  Write-LocalDictationInstallProgress -PercentComplete 50 -Status "Skipping speech model preparation. Dictation will need a model later."
}

if ($WithOllama) {
  Write-LocalDictationInstallProgress -PercentComplete 70 -Status "Preparing local cleanup with Ollama. This can take longer and may install Ollama through winget."
  Invoke-LocalDictationCli -Arguments @("setup", "bootstrap", "--ollama-only", "--enable-cleanup")
}

if ($NoStartup) {
  Write-LocalDictationInstallProgress -PercentComplete 82 -Status "Startup is disabled because -NoStartup was used."
}
else {
  Write-LocalDictationInstallProgress -PercentComplete 82 -Status "Startup is enabled for your Windows sign-in."
}

if ($NoLaunch) {
  Write-LocalDictationInstallProgress -PercentComplete 95 -Status "Launch skipped because -NoLaunch was used."
}
else {
  Write-LocalDictationInstallProgress -PercentComplete 90 -Status "Launching Local Dictation."
  Start-LocalDictationApp
  $localGuiUrl = Test-LocalDictationLocalGui
  if ($localGuiUrl) {
    Write-Host "Localhost UI is available at $localGuiUrl."
  }
  else {
    Write-Host "Localhost UI did not respond after launch. Dictation may still work from the tray and hotkey. Check %APPDATA%\LocalDictation\logs\local-dictation.log or run Doctor from the Start Menu."
  }
}

Write-LocalDictationInstallProgress -PercentComplete 100 -Status "Local Dictation install is complete."
Write-Progress -Activity "Installing Local Dictation" -Completed