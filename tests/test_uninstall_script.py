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


def test_uninstall_script_removes_ollama_user_roots_unless_kept():
    script = _script_text()

    keep_ollama = script.index("if ($KeepOllama)")
    ollama_paths = script.index("function Get-LocalDictationOllamaPaths")
    cleanup_call = script.index("foreach ($path in Get-LocalDictationOllamaPaths)")

    assert ollama_paths < cleanup_call
    assert keep_ollama < cleanup_call
    assert 'Join-Path $HOME ".ollama"' in script