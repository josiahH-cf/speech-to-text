param(
  [switch]$InstallTools,
  [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (!(Test-Path ".\.venv\Scripts\python.exe")) {
  py -3.12 -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,build]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall -q src tests

Push-Location packaging
try {
  ..\.venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath ..\dist --workpath ..\build\pyinstaller LocalDictation.spec
}
finally {
  Pop-Location
}

if ($SkipInstaller) {
  Write-Host "PyInstaller bundle built at dist\LocalDictation"
  exit 0
}

$isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$isccPath = if ($isccCommand) { $isccCommand.Source } else { $null }
if (-not $isccPath -and $InstallTools) {
  winget install --id JRSoftware.InnoSetup --exact --silent --accept-package-agreements --accept-source-agreements
  $isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
  $isccPath = if ($isccCommand) { $isccCommand.Source } else { $null }
  if (-not $isccPath) {
    $candidates = @(
      (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
      (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
      (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    foreach ($candidate in $candidates) {
      if (Test-Path $candidate) {
        $isccPath = $candidate
        break
      }
    }
  }
}

if (-not $isccPath) {
  $candidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
  )
  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      $isccPath = $candidate
      break
    }
  }
}

if (-not $isccPath) {
  throw "ISCC.exe was not found. Install Inno Setup 6 or rerun with -InstallTools."
}

& $isccPath packaging\LocalDictation.iss
Write-Host "Installer built at dist\installer\LocalDictationSetup-0.2.0.exe"
