$Script:LocalDictationRepoRoot = Split-Path -Parent $PSScriptRoot
$Script:LocalDictationVenvPython = Join-Path $Script:LocalDictationRepoRoot ".venv\Scripts\python.exe"

function Set-LocalDictationRepoRoot {
  Set-Location $Script:LocalDictationRepoRoot
}

function Assert-LocalDictationPython312 {
  if (!(Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.12 and ensure the Python launcher is available on PATH."
  }

  & py -3.12 --version *> $null
  if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12 was not found through 'py -3.12'. Install Python 3.12 or repair the Python launcher registration."
  }
}

function Get-LocalDictationVenvPython {
  if (!(Test-Path $Script:LocalDictationVenvPython)) {
    throw "Virtual environment was not found. Run .\scripts\install.ps1 first."
  }
  return $Script:LocalDictationVenvPython
}