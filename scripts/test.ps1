$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"
Set-LocalDictationRepoRoot
$python = Get-LocalDictationVenvPython

$pytestArgs = @($args)
if ($pytestArgs.Count -eq 0) {
  $pytestArgs = @("-q")
}

& $python -m pytest @pytestArgs
exit $LASTEXITCODE
