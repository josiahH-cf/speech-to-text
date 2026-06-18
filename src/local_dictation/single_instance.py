from __future__ import annotations

import logging
from typing import Any

try:  # pragma: no cover - import guard exercised only off-Windows
    import win32api
    import win32event
    import winerror
except ImportError:  # pragma: no cover - pywin32 is present on Windows targets
    win32api = None  # type: ignore[assignment]
    win32event = None  # type: ignore[assignment]
    winerror = None  # type: ignore[assignment]

# Per-session mutex name: prevents a second instance within the same Windows
# sign-in session, which is exactly the case when both the Run key and the
# Scheduled Task fire at logon.
DEFAULT_MUTEX_NAME = "Local\\LocalDictation-SingleInstance"

# The mutex handle must outlive this function call; Windows releases the named
# mutex when the owning process exits, so we keep it for the process lifetime.
_held_handle: Any = None


def acquire_single_instance(name: str = DEFAULT_MUTEX_NAME, *, logger: logging.Logger | None = None) -> bool:
    """Try to claim the single-instance lock for this process.

    Returns ``True`` when this process owns the lock and may continue starting,
    or ``False`` when another Local Dictation instance already holds it. When the
    guard cannot be created (for example pywin32 is unavailable), startup is
    allowed so the app never becomes unusable because of the guard.
    """
    global _held_handle
    log = logger or logging.getLogger(__name__)

    if win32event is None or win32api is None or winerror is None:
        log.warning("Single-instance guard unavailable (pywin32 missing); continuing without it.")
        return True

    try:
        handle = win32event.CreateMutex(None, False, name)
        last_error = win32api.GetLastError()
    except Exception as exc:  # pragma: no cover - defensive, win32 call failure
        log.warning("Single-instance guard could not be created: %s", exc)
        return True

    if last_error == winerror.ERROR_ALREADY_EXISTS:
        log.info("Another Local Dictation instance is already running; this one will exit.")
        return False

    _held_handle = handle
    return True
