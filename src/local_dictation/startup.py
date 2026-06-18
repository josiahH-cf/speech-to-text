from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

APP_RUN_VALUE_NAME = "LocalDictation"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
TASK_NAME = "LocalDictation"
TASK_DESCRIPTION = "Starts Local Dictation when you sign in to Windows."


def startup_python_executable() -> Path:
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            return pythonw
    return exe


def startup_program_and_args(python_exe: str | Path | None = None) -> tuple[str, str]:
    """Return the executable and argument string used to launch the resident app."""
    if getattr(sys, "frozen", False) and python_exe is None:
        app_exe = Path(sys.executable)
        if app_exe.name.lower() == "localdictationcli.exe":
            sibling = app_exe.with_name("LocalDictation.exe")
            if sibling.exists():
                app_exe = sibling
        return str(app_exe), "run"
    exe = Path(python_exe) if python_exe else startup_python_executable()
    return str(exe), "-m local_dictation run"


def build_startup_command(python_exe: str | Path | None = None) -> str:
    program, arguments = startup_program_and_args(python_exe)
    if arguments:
        return f'"{program}" {arguments}'
    return f'"{program}"'


# --- Sign-in Run key -------------------------------------------------------


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


# --- Logon Scheduled Task --------------------------------------------------


def current_user() -> str:
    domain = os.environ.get("USERDOMAIN")
    user = os.environ.get("USERNAME") or ""
    if not user:
        import getpass

        user = getpass.getuser()
    if domain and "\\" not in user:
        return f"{domain}\\{user}"
    return user


def _split_command(command: str) -> tuple[str, str]:
    command = command.strip()
    if command.startswith('"'):
        end = command.find('"', 1)
        if end != -1:
            return command[1:end], command[end + 1 :].strip()
    program, _, arguments = command.partition(" ")
    return program, arguments.strip()


def build_scheduled_task_xml(program: str, arguments: str = "", *, user: str | None = None) -> str:
    user = user or current_user()
    program_xml = escape(program)
    user_xml = escape(user)
    arguments_node = f"\n      <Arguments>{escape(arguments)}</Arguments>" if arguments else ""
    return (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
        "  <RegistrationInfo>\n"
        f"    <Description>{escape(TASK_DESCRIPTION)}</Description>\n"
        "  </RegistrationInfo>\n"
        "  <Triggers>\n"
        "    <LogonTrigger>\n"
        "      <Enabled>true</Enabled>\n"
        f"      <UserId>{user_xml}</UserId>\n"
        "      <Delay>PT5S</Delay>\n"
        "    </LogonTrigger>\n"
        "  </Triggers>\n"
        "  <Principals>\n"
        '    <Principal id="Author">\n'
        f"      <UserId>{user_xml}</UserId>\n"
        "      <LogonType>InteractiveToken</LogonType>\n"
        "      <RunLevel>LeastPrivilege</RunLevel>\n"
        "    </Principal>\n"
        "  </Principals>\n"
        "  <Settings>\n"
        "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n"
        "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
        "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
        "    <AllowHardTerminate>false</AllowHardTerminate>\n"
        "    <StartWhenAvailable>true</StartWhenAvailable>\n"
        "    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\n"
        "    <IdleSettings>\n"
        "      <StopOnIdleEnd>false</StopOnIdleEnd>\n"
        "      <RestartOnIdle>false</RestartOnIdle>\n"
        "    </IdleSettings>\n"
        "    <AllowStartOnDemand>true</AllowStartOnDemand>\n"
        "    <Enabled>true</Enabled>\n"
        "    <Hidden>false</Hidden>\n"
        "    <RunOnlyIfIdle>false</RunOnlyIfIdle>\n"
        "    <RestartOnFailure>\n"
        "      <Interval>PT1M</Interval>\n"
        "      <Count>3</Count>\n"
        "    </RestartOnFailure>\n"
        "    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>\n"
        "    <Priority>7</Priority>\n"
        "  </Settings>\n"
        '  <Actions Context="Author">\n'
        "    <Exec>\n"
        f"      <Command>{program_xml}</Command>{arguments_node}\n"
        "    </Exec>\n"
        "  </Actions>\n"
        "</Task>\n"
    )


def scheduled_task_create_command(xml_path: str) -> list[str]:
    return ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", xml_path, "/F"]


def scheduled_task_delete_command() -> list[str]:
    return ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]


def scheduled_task_query_command() -> list[str]:
    return ["schtasks", "/Query", "/TN", TASK_NAME]


def _run_schtasks(command: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "schtasks.exe was not found."
    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode == 0:
        return True, output or "ok"
    return False, output or f"exit code {completed.returncode}"


def scheduled_task_exists() -> bool:
    ok, _message = _run_schtasks(scheduled_task_query_command())
    return ok


def enable_scheduled_task(command: str | None = None) -> tuple[bool, str]:
    if command is None:
        program, arguments = startup_program_and_args()
    else:
        program, arguments = _split_command(command)
    xml = build_scheduled_task_xml(program, arguments)
    fd, path = tempfile.mkstemp(suffix=".xml", prefix="localdictation-task-")
    try:
        with os.fdopen(fd, "w", encoding="utf-16") as handle:
            handle.write(xml)
        return _run_schtasks(scheduled_task_create_command(path))
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def disable_scheduled_task() -> tuple[bool, str]:
    if not scheduled_task_exists():
        return True, "not present"
    return _run_schtasks(scheduled_task_delete_command())
