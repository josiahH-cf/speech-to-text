from __future__ import annotations

import sys
from pathlib import Path

APP_RUN_VALUE_NAME = "LocalDictation"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def startup_python_executable() -> Path:
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            return pythonw
    return exe


def build_startup_command(python_exe: str | Path | None = None) -> str:
    if getattr(sys, "frozen", False) and python_exe is None:
        app_exe = Path(sys.executable)
        if app_exe.name.lower() == "localdictationcli.exe":
            sibling = app_exe.with_name("LocalDictation.exe")
            if sibling.exists():
                app_exe = sibling
        return f'"{app_exe}" run'
    exe = Path(python_exe) if python_exe else startup_python_executable()
    return f'"{exe}" -m local_dictation run'


def enable_startup(command: str | None = None) -> None:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_RUN_VALUE_NAME, 0, winreg.REG_SZ, command or build_startup_command())


def disable_startup() -> None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_RUN_VALUE_NAME)
    except FileNotFoundError:
        return


def startup_command() -> str | None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, APP_RUN_VALUE_NAME)
            return str(value)
    except FileNotFoundError:
        return None


def is_startup_enabled() -> bool:
    return startup_command() is not None
