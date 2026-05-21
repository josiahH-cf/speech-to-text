param(
  [switch]$InstallTools,
  [switch]$SkipInstaller,
  [string]$CodeSigningCertThumbprint = "",
  [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"
Set-LocalDictationRepoRoot
Assert-LocalDictationPython312

function Get-LocalDictationSignTool {
  $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
  if ($command) {
    return $command.Source
  }

  $candidates = @()
  $kitsRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
  if (Test-Path $kitsRoot) {
    $candidates = Get-ChildItem -Path $kitsRoot -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
      Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
      Sort-Object FullName -Descending
  }
  if ($candidates.Count -gt 0) {
    return $candidates[0].FullName
  }

  return $null
}

function Invoke-LocalDictationCodeSign {
  param(
    [string[]]$Paths,
    [string]$CertThumbprint = "",
    [string]$TsUrl = ""
  )

  if ([string]::IsNullOrWhiteSpace($CertThumbprint)) {
    return
  }

  $signTool = Get-LocalDictationSignTool
  if (-not $signTool) {
    throw "signtool.exe was not found. Install the Windows SDK or omit -CodeSigningCertThumbprint."
  }
  foreach ($path in $Paths) {
    if (!(Test-Path $path)) {
      continue
    }
    $arguments = @("sign", "/sha1", $CertThumbprint, "/fd", "SHA256")
    if (![string]::IsNullOrWhiteSpace($TsUrl)) {
      $arguments += @("/tr", $TsUrl, "/td", "SHA256")
    }
    $arguments += $path
    & $signTool @arguments
  }
}

function Write-LocalDictationReleaseEvidence {
  param(
    [string]$PythonPath,
    [string[]]$ArtifactPaths
  )

  $evidenceDir = "dist\release-evidence"
  New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

  $existingArtifacts = @($ArtifactPaths | Where-Object { Test-Path $_ })
  $checksumLines = foreach ($artifact in $existingArtifacts) {
    $hash = Get-FileHash -Algorithm SHA256 -Path $artifact
    "$($hash.Hash.ToLowerInvariant())  $artifact"
  }
  Set-Content -Path (Join-Path $evidenceDir "CHECKSUMS.sha256") -Value $checksumLines -Encoding utf8

  $signatureLines = foreach ($artifact in $existingArtifacts) {
    $signature = Get-AuthenticodeSignature -FilePath $artifact
    $subject = if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { "<unsigned>" }
    "$artifact`tStatus=$($signature.Status)`tSigner=$subject"
  }
  Set-Content -Path (Join-Path $evidenceDir "SIGNATURES.txt") -Value $signatureLines -Encoding utf8

  $commit = "unknown"
  if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitOutput = & git rev-parse HEAD 2>$null
    if ($LASTEXITCODE -eq 0 -and $gitOutput) {
      $commit = ($gitOutput | Select-Object -First 1).Trim()
    }
  }

  $pythonVersion = & $PythonPath --version
  $pyInstallerVersion = & $PythonPath -c "import PyInstaller; print(PyInstaller.__version__)"
  $dependencies = & $PythonPath -c "import pathlib, tomllib; data=tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8')); print('\n'.join(data['project'].get('dependencies', [])))"
  Set-Content -Path (Join-Path $evidenceDir "DIRECT-DEPENDENCIES.txt") -Value $dependencies -Encoding utf8

  $provenance = @(
    "Local Dictation build provenance",
    "BuiltAt=$((Get-Date).ToString('o'))",
    "GitCommit=$commit",
    "Python=$pythonVersion",
    "PyInstaller=$pyInstallerVersion",
    "UPX=disabled",
    "SigningRequested=$(![string]::IsNullOrWhiteSpace($CodeSigningCertThumbprint))"
  )
  Set-Content -Path (Join-Path $evidenceDir "BUILD-PROVENANCE.txt") -Value $provenance -Encoding utf8
  Write-Host "Release evidence written to $evidenceDir"
}

if ([string]::IsNullOrWhiteSpace($CodeSigningCertThumbprint)) {
  Write-Warning "No code signing certificate thumbprint supplied; build artifacts will be unsigned."
}

if (!(Test-Path ".\.venv\Scripts\python.exe")) {
  py -3.12 -m venv .venv
}

$python = Get-LocalDictationVenvPython
& $python -m pip install --upgrade pip
& $python -m pip install -e ".[dev,build]"
& $python -m pytest
& $python -m compileall -q src tests

Push-Location packaging
try {
  ..\.venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath ..\dist --workpath ..\build\pyinstaller LocalDictation.spec
}
finally {
  Pop-Location
}

$exeArtifacts = @(
  "dist\LocalDictation\LocalDictation.exe",
  "dist\LocalDictation\LocalDictationCLI.exe"
)
Invoke-LocalDictationCodeSign -Paths $exeArtifacts -CertThumbprint $CodeSigningCertThumbprint -TsUrl $TimestampUrl

if ($SkipInstaller) {
  Write-LocalDictationReleaseEvidence -PythonPath $python -ArtifactPaths $exeArtifacts
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
$installerArtifact = Get-ChildItem -Path "dist\installer" -Filter "LocalDictationSetup-*.exe" -File -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName
if (!$installerArtifact) {
  throw "Inno Setup did not produce an installer under dist\installer. Check the build output above."
}
Invoke-LocalDictationCodeSign -Paths @($installerArtifact) -CertThumbprint $CodeSigningCertThumbprint -TsUrl $TimestampUrl
Write-LocalDictationReleaseEvidence -PythonPath $python -ArtifactPaths ($exeArtifacts + @($installerArtifact))
Write-Host "Installer built at $installerArtifact"
