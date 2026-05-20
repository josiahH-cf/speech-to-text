from __future__ import annotations

import shutil
import subprocess
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from .cleanup import check_ollama
from .config import load_settings, save_settings
from .transcriber import FasterWhisperTranscriber


@dataclass(frozen=True)
class SetupStep:
    name: str
    ok: bool
    message: str


@dataclass(frozen=True)
class SetupStatus:
    steps: tuple[SetupStep, ...]

    @property
    def ok(self) -> bool:
        return all(step.ok for step in self.steps)

    def render(self) -> str:
        lines = ["Local Dictation setup status"]
        for step in self.steps:
            lines.append(f"{'OK' if step.ok else 'FAIL'} {step.name}: {step.message}")
        return "\n".join(lines)


def command_available(command: str) -> bool:
    return command_path(command) is not None


def command_path(command: str) -> str | None:
    found = shutil.which(command)
    if found:
        return found
    if command.lower() == "ollama":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe")
            if os.path.exists(candidate):
                return candidate
    return None


def winget_install_ollama_command() -> list[str]:
    return [
        "winget",
        "install",
        "--id",
        "Ollama.Ollama",
        "--exact",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]


def ollama_pull_command(model: str) -> list[str]:
    return ["ollama", "pull", model]


def run_command(command: Sequence[str], timeout_seconds: int = 900) -> tuple[bool, str]:
    command = list(command)
    resolved = command_path(command[0])
    if resolved:
        command[0] = resolved
    try:
        completed = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return False, f"Command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        return False, f"Timed out after {timeout_seconds} seconds: {' '.join(command)}"

    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode == 0:
        return True, output or "completed"
    return False, output or f"exit code {completed.returncode}"


def collect_setup_status(
    settings: dict | None = None,
    *,
    include_stt: bool = True,
    include_ollama: bool = False,
) -> SetupStatus:
    settings = settings or load_settings(create=True)
    setup = settings.get("setup", {})
    cleanup = settings.get("cleanup", {})
    steps: list[SetupStep] = []
    if include_stt:
        steps.append(
            SetupStep("STT model", bool(setup.get("stt_model_ready", False)), settings.get("stt", {}).get("model", "base.en"))
        )
    if include_ollama:
        steps.extend(
            [
                SetupStep("winget", command_available("winget"), "available" if command_available("winget") else "not found"),
                SetupStep(
                    "Ollama executable", command_available("ollama"), "available" if command_available("ollama") else "not found"
                ),
            ]
        )
        reachable, message = check_ollama(cleanup.get("endpoint", "http://localhost:11434/api/generate"), timeout_seconds=2)
        steps.append(SetupStep("Ollama API", reachable, message))
    return SetupStatus(tuple(steps))


def bootstrap_setup(
    settings: dict | None = None,
    *,
    logger=None,
    include_stt: bool = True,
    include_ollama: bool = True,
) -> SetupStatus:
    settings = settings or load_settings(create=True)
    setup = settings.setdefault("setup", {})
    steps: list[SetupStep] = []

    if include_stt:
        try:
            transcriber = FasterWhisperTranscriber(settings.get("stt", {}), logger=logger)
            transcriber.download_model()
            setup["stt_model_ready"] = True
            steps.append(SetupStep("STT model", True, f"{settings.get('stt', {}).get('model', 'base.en')} is ready"))
        except Exception as exc:
            setup["stt_model_ready"] = False
            steps.append(SetupStep("STT model", False, str(exc)))

    cleanup = settings.setdefault("cleanup", {})
    ollama_mode = setup.get("ollama_install", "auto")
    if include_ollama and ollama_mode == "auto":
        if not command_available("ollama"):
            if command_available("winget"):
                ok, message = run_command(winget_install_ollama_command())
                steps.append(SetupStep("Install Ollama", ok, message))
            else:
                ok = False
                message = "winget is not available"
                steps.append(SetupStep("Install Ollama", False, message))
        else:
            ok = True
            message = "Ollama executable is available"
            steps.append(SetupStep("Install Ollama", True, message))

        if ok and command_available("ollama"):
            model = cleanup.get("model", "gemma3:1b")
            ok, message = run_command(ollama_pull_command(model))
            setup["ollama_ready"] = bool(ok)
            steps.append(SetupStep("Ollama model", ok, message or model))
        else:
            setup["ollama_ready"] = False
    elif include_ollama:
        steps.append(SetupStep("Ollama", True, f"install mode is {ollama_mode}"))

    setup["last_bootstrap_status"] = {
        "when": datetime.now().isoformat(timespec="seconds"),
        "ok": all(step.ok for step in steps),
        "steps": [step.__dict__ for step in steps],
    }
    save_settings(settings)
    return SetupStatus(tuple(steps))
