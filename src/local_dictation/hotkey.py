from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

MODIFIER_TOKENS = {
    "alt": MOD_ALT,
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
    "meta": MOD_WIN,
}

KEY_CODES = {
    "backspace": 0x08,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "escape": 0x1B,
    "esc": 0x1B,
    "space": 0x20,
    "pageup": 0x21,
    "pagedown": 0x22,
    "end": 0x23,
    "home": 0x24,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "insert": 0x2D,
    "delete": 0x2E,
}
KEY_CODES.update({chr(code): code for code in range(ord("a"), ord("z") + 1)})
KEY_CODES.update({str(i): ord(str(i)) for i in range(10)})
KEY_CODES.update({f"f{i}": 0x70 + i - 1 for i in range(1, 25)})


class HotkeyError(ValueError):
    """Raised for invalid hotkey configuration."""


class HotkeyRegistrationError(RuntimeError):
    """Raised when Windows rejects hotkey registration."""


@dataclass(frozen=True)
class HotkeyBinding:
    modifiers: int
    vk: int
    normalized: str


def parse_hotkey(hotkey: str) -> HotkeyBinding:
    tokens = [part.strip().lower() for part in hotkey.replace("-", "+").split("+") if part.strip()]
    if not tokens:
        raise HotkeyError("Hotkey cannot be empty.")

    modifiers = 0
    key_token: str | None = None
    for token in tokens:
        if token in MODIFIER_TOKENS:
            modifiers |= MODIFIER_TOKENS[token]
            continue
        if key_token is not None:
            raise HotkeyError(f"Hotkey has more than one non-modifier key: {hotkey}")
        key_token = token

    if key_token is None:
        raise HotkeyError(f"Hotkey must include a non-modifier key: {hotkey}")
    if key_token == "f12":
        raise HotkeyError("F12 is reserved by Windows debugging tools and cannot be used.")
    if key_token not in KEY_CODES:
        raise HotkeyError(f"Unsupported hotkey key: {key_token}")

    normalized_parts: list[str] = []
    if modifiers & MOD_CONTROL:
        normalized_parts.append("ctrl")
    if modifiers & MOD_ALT:
        normalized_parts.append("alt")
    if modifiers & MOD_SHIFT:
        normalized_parts.append("shift")
    if modifiers & MOD_WIN:
        normalized_parts.append("win")
    normalized_parts.append(key_token)

    return HotkeyBinding(
        modifiers=modifiers | MOD_NOREPEAT,
        vk=KEY_CODES[key_token],
        normalized="+".join(normalized_parts),
    )


def _hotkey_message_values(message: object) -> tuple[int, int]:
    message_code = getattr(message, "message", None)
    w_param = getattr(message, "wParam", None)
    if message_code is not None and w_param is not None:
        return int(message_code), int(w_param)

    if isinstance(message, tuple) and len(message) >= 3:
        return int(message[1]), int(message[2])

    raise HotkeyRegistrationError(f"Unexpected Windows message shape: {message!r}")


class GlobalHotkeyListener:
    def __init__(
        self,
        hotkey: str,
        callback: Callable[[], None],
        *,
        logger: logging.Logger | None = None,
        hotkey_id: int = 1,
    ) -> None:
        self.binding = parse_hotkey(hotkey)
        self.callback = callback
        self.logger = logger or logging.getLogger(__name__)
        self.hotkey_id = hotkey_id
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._error: BaseException | None = None
        self._registered = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="global-hotkey", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)
        if self._error:
            raise self._error
        if not self._registered:
            raise HotkeyRegistrationError("Timed out while registering global hotkey.")

    def stop(self) -> None:
        self._stop.set()
        if self._thread_id is not None:
            try:
                import win32api
                import win32con

                win32api.PostThreadMessage(self._thread_id, win32con.WM_QUIT, 0, 0)
            except Exception as exc:  # pragma: no cover - Windows API cleanup path
                self.logger.debug("Could not post WM_QUIT to hotkey thread: %s", exc)
        if self._thread and threading.current_thread() is not self._thread:
            self._thread.join(timeout=2)

    def is_listener_thread(self) -> bool:
        return threading.current_thread() is self._thread

    def _run(self) -> None:  # pragma: no cover - requires Windows message loop
        try:
            import win32api
            import win32con
            import win32gui

            self._thread_id = win32api.GetCurrentThreadId()
            try:
                win32gui.RegisterHotKey(
                    None,
                    self.hotkey_id,
                    self.binding.modifiers,
                    self.binding.vk,
                )
            except Exception as exc:
                code = getattr(exc, "winerror", None) or win32api.GetLastError()
                raise HotkeyRegistrationError(
                    f"Could not register hotkey {self.binding.normalized}; Windows error {code}: {exc}"
                ) from exc

            self._registered = True
            self._ready.set()
            self.logger.info("Registered global hotkey %s", self.binding.normalized)

            while not self._stop.is_set():
                status, msg = win32gui.GetMessage(None, 0, 0)
                if status == 0:
                    break
                if status == -1:
                    raise HotkeyRegistrationError("Windows GetMessage failed in hotkey loop.")
                message_code, w_param = _hotkey_message_values(msg)
                if message_code == win32con.WM_HOTKEY and w_param == self.hotkey_id:
                    self.callback()
        except BaseException as exc:
            self._error = exc
            self._ready.set()
            self.logger.exception("Hotkey listener stopped with an error.")
        finally:
            if self._registered:
                try:
                    import win32gui

                    win32gui.UnregisterHotKey(None, self.hotkey_id)
                    self.logger.info("Unregistered global hotkey %s", self.binding.normalized)
                except Exception as exc:
                    self.logger.debug("Could not unregister hotkey: %s", exc)
            self._registered = False
