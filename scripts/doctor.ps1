$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"
Set-LocalDictationRepoRoot
$python = Get-LocalDictationVenvPython
& $python -m local_dictation doctor
