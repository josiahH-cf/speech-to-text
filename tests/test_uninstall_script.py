from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "uninstall-user.ps1"


def _script_text() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_uninstall_script_does_not_delegate_data_cleanup_to_installed_cli():
    script = _script_text()

    assert "cleanup-data" not in script
    assert "Invoke-LocalDictationCleanupData" not in script


def test_uninstall_script_removes_app_data_after_uninstaller():
    script = _script_text()

    uninstaller_step = script.index('Status "Running the Local Dictation uninstaller."')
    data_cleanup_step = script.index('Status "Removing app data and model caches."')

    assert data_cleanup_step > uninstaller_step
    assert "Remove-LocalDictationData" in script[data_cleanup_step:]
    assert "Assert-LocalDictationPathRemoved -Path $appDataDir" in script


def test_uninstall_script_falls_back_when_installed_cli_is_blocked():
    script = _script_text()

    assert "try {" in script
    assert "could not disable startup; removing startup registry entry directly" in script
    cli_disable = script.index("& $cli startup disable")
    registry_cleanup = script.index("Remove-ItemProperty")
    assert cli_disable < registry_cleanup


def test_uninstall_script_cleans_artifacts_if_uninstaller_is_blocked():
    script = _script_text()

    assert "Local Dictation uninstaller could not run; removing installed files directly" in script
    assert "function Remove-LocalDictationInstallArtifacts" in script
    assert '[Environment]::GetFolderPath("Programs")' in script
    assert '[Environment]::GetFolderPath("Desktop")' in script
    assert "{6C9EC15F-627D-4669-B5D9-C986181593B3}_is1" in script
    install_dir_removed = script.index("Assert-LocalDictationPathRemoved -Path $installDir")
    artifacts_removed = script.index("Remove-LocalDictationInstallArtifacts", install_dir_removed)
    data_cleanup = script.index('Status "Removing app data and model caches."')
    assert install_dir_removed < artifacts_removed < data_cleanup


def test_uninstall_script_removes_ollama_user_roots_unless_kept():
    script = _script_text()

    keep_ollama = script.index("if ($KeepOllama)")
    ollama_paths = script.index("function Get-LocalDictationOllamaPaths")
    cleanup_call = script.index("foreach ($path in Get-LocalDictationOllamaPaths)")

    assert ollama_paths < cleanup_call
    assert keep_ollama < cleanup_call
    assert 'Join-Path $HOME ".ollama"' in script