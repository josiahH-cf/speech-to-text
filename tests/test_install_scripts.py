from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _script_text(name: str) -> str:
    return (SCRIPTS_DIR / name).read_text(encoding="utf-8")


def test_install_user_auto_build_guard_present():
    """install-user.ps1 invokes build-installer.ps1 when no installer exists."""
    script = _script_text("install-user.ps1")
    assert "build-installer.ps1" in script


def test_install_user_explicit_path_error_mentions_auto_build():
    """The explicit-path error message guides the user toward the auto-build path."""
    script = _script_text("install-user.ps1")
    assert "auto-build" in script


def test_build_installer_artifact_path_is_not_hardcoded():
    """build-installer.ps1 must not reference a version-specific installer filename."""
    script = _script_text("build-installer.ps1")
    assert "LocalDictationSetup-0.2.0.exe" not in script


def test_install_user_local_gui_health_uses_active_url_and_retries():
    """install-user.ps1 must wait for launch and report the recovered localhost URL."""
    script = _script_text("install-user.ps1")
    assert "local-gui.json" in script
    assert "/api/ping" in script
    assert "/api/state" in script
    assert "sttModel" in script
    assert "[int]$Attempts = 60" in script
    assert "Start-Sleep" in script
    assert "return $normalizedUrl" in script
    assert "Localhost UI is available at $localGuiUrl" in script


def test_install_user_stops_running_processes_before_installer():
    """install-user.ps1 must stop LocalDictation processes before running the installer."""
    script = _script_text("install-user.ps1")
    assert 'Get-Process -Name "LocalDictation", "LocalDictationCLI" -ErrorAction SilentlyContinue | Stop-Process -Force' in script
    stop_pos = script.index("Stop-Process -Force")
    installer_pos = script.index("Start-Process -FilePath $installer")
    assert stop_pos < installer_pos


def test_smoke_test_uses_active_localhost_url():
    """smoke-test.ps1 must check the active recovered localhost URL when present."""
    script = _script_text("smoke-test.ps1")
    assert "local-gui.json" in script
    assert "/api/ping" in script
    assert "/api/state" in script
    assert "sttModel" in script
    assert "python -m local_dictation gui" in script
