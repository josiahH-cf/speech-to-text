from __future__ import annotations

import sys
from pathlib import Path


def packaged_executable(*, console: bool) -> Path:
    exe = Path(sys.executable)
    if not getattr(sys, "frozen", False):
        return exe

    if console:
        sibling = exe.with_name("LocalDictationCLI.exe")
        if sibling.exists():
            return sibling
        return exe

    if exe.name.lower() == "localdictationcli.exe":
        sibling = exe.with_name("LocalDictation.exe")
        if sibling.exists():
            return sibling
    return exe


def app_command(*args: str, console: bool = False) -> list[str]:
    exe = packaged_executable(console=console)
    if getattr(sys, "frozen", False):
        return [str(exe), *args]
    return [str(exe), "-m", "local_dictation", *args]
