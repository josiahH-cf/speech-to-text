from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable


@dataclass(frozen=True)
class InsertionResult:
    inserted: bool
    copied_to_clipboard: bool
    message: str


@dataclass(frozen=True)
class ClipboardItem:
    format_id: int
    data: object


@dataclass(frozen=True)
class ClipboardSnapshot:
    items: tuple[ClipboardItem, ...]

    @property
    def has_items(self) -> bool:
        return bool(self.items)


class IntegrityLevel(IntEnum):
    UNKNOWN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    SYSTEM = 4


CF_TEXT = 1
CF_BITMAP = 2
CF_DIB = 8
CF_UNICODETEXT = 13
CF_HDROP = 15

COMMON_CLIPBOARD_FORMATS = (CF_UNICODETEXT, CF_HDROP, CF_DIB)


def should_restore_text_clipboard(restore_enabled: bool, previous_text: str | None, inserted_text: str) -> bool:
    return bool(restore_enabled and previous_text is not None and previous_text != inserted_text)


def classify_integrity_rid(rid: int | None) -> IntegrityLevel:
    if rid is None:
        return IntegrityLevel.UNKNOWN
    if rid >= 0x4000:
        return IntegrityLevel.SYSTEM
    if rid >= 0x3000:
        return IntegrityLevel.HIGH
    if rid >= 0x2000:
        return IntegrityLevel.MEDIUM
    if rid >= 0x1000:
        return IntegrityLevel.LOW
    return IntegrityLevel.UNKNOWN


def can_inject_into_target(current: IntegrityLevel, target: IntegrityLevel) -> bool:
    if current == IntegrityLevel.UNKNOWN or target == IntegrityLevel.UNKNOWN:
        return True
    return current >= target


def capture_foreground_window() -> int | None:
    try:
        import win32gui

        hwnd = win32gui.GetForegroundWindow()
        return int(hwnd) if hwnd else None
    except Exception:
        return None


def _token_integrity_level(token) -> IntegrityLevel:
    import win32security

    sid = win32security.GetTokenInformation(token, win32security.TokenIntegrityLevel)
    if isinstance(sid, tuple):
        sid = sid[0]
    count = sid.GetSubAuthorityCount()
    return classify_integrity_rid(int(sid.GetSubAuthority(count - 1)))


def current_process_integrity_level() -> IntegrityLevel:
    try:
        import win32api
        import win32security

        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), 0x0008)
        try:
            return _token_integrity_level(token)
        finally:
            try:
                token.Close()
            except Exception:
                pass
    except Exception:
        return IntegrityLevel.UNKNOWN


def target_window_integrity_level(hwnd: int | None) -> IntegrityLevel:
    if not hwnd:
        return IntegrityLevel.UNKNOWN
    try:
        import win32api
        import win32process
        import win32security

        _thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
        handle = win32api.OpenProcess(0x1000, False, pid)
        try:
            token = win32security.OpenProcessToken(handle, 0x0008)
            try:
                return _token_integrity_level(token)
            finally:
                try:
                    token.Close()
                except Exception:
                    pass
        finally:
            try:
                handle.Close()
            except Exception:
                pass
    except Exception:
        return IntegrityLevel.UNKNOWN


def restore_focus(hwnd: int | None, timeout_ms: int, *, logger: logging.Logger | None = None) -> bool:
    if not hwnd:
        return False
    log = logger or logging.getLogger(__name__)
    try:
        import win32gui

        if int(win32gui.GetForegroundWindow()) == int(hwnd):
            return True
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception as exc:
            log.warning("SetForegroundWindow failed: %s", exc)

        deadline = time.monotonic() + max(0, timeout_ms) / 1000
        while time.monotonic() <= deadline:
            if int(win32gui.GetForegroundWindow()) == int(hwnd):
                return True
            time.sleep(0.05)
    except Exception as exc:
        log.warning("Could not restore focus: %s", exc)
    return False


def get_clipboard_text() -> str | None:
    import win32clipboard

    win32clipboard.OpenClipboard()
    try:
        if not win32clipboard.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None
        return win32clipboard.GetClipboardData(CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()


def snapshot_clipboard(formats: Iterable[int] = COMMON_CLIPBOARD_FORMATS) -> ClipboardSnapshot:
    import win32clipboard

    items: list[ClipboardItem] = []
    win32clipboard.OpenClipboard()
    try:
        for format_id in formats:
            try:
                if win32clipboard.IsClipboardFormatAvailable(format_id):
                    items.append(ClipboardItem(format_id, win32clipboard.GetClipboardData(format_id)))
            except Exception:
                continue
    finally:
        win32clipboard.CloseClipboard()
    return ClipboardSnapshot(tuple(items))


def restore_clipboard_snapshot(snapshot: ClipboardSnapshot, *, logger: logging.Logger | None = None) -> bool:
    if not snapshot.has_items:
        return False
    import win32clipboard

    log = logger or logging.getLogger(__name__)
    restored = False
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        for item in snapshot.items:
            try:
                if item.format_id == CF_UNICODETEXT and isinstance(item.data, str):
                    win32clipboard.SetClipboardText(item.data, CF_UNICODETEXT)
                else:
                    win32clipboard.SetClipboardData(item.format_id, item.data)
                restored = True
            except Exception as exc:
                log.warning("Could not restore clipboard format %s: %s", item.format_id, exc)
    finally:
        win32clipboard.CloseClipboard()
    return restored


def set_clipboard_text(text: str) -> None:
    import win32clipboard

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()


def utf16_units(text: str) -> list[int]:
    data = text.encode("utf-16-le")
    return [int.from_bytes(data[index : index + 2], "little") for index in range(0, len(data), 2)]


def _keyboard_input_classes():
    input_keyboard = 1
    ulong_ptr = ctypes.wintypes.WPARAM

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.wintypes.WORD),
            ("wScan", ctypes.wintypes.WORD),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("time", ctypes.wintypes.DWORD),
            ("dwExtraInfo", ulong_ptr),
        ]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.wintypes.LONG),
            ("dy", ctypes.wintypes.LONG),
            ("mouseData", ctypes.wintypes.DWORD),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("time", ctypes.wintypes.DWORD),
            ("dwExtraInfo", ulong_ptr),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", ctypes.wintypes.DWORD),
            ("wParamL", ctypes.wintypes.WORD),
            ("wParamH", ctypes.wintypes.WORD),
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.wintypes.DWORD), ("union", INPUT_UNION)]

    return INPUT, KEYBDINPUT, input_keyboard


def _send_inputs(inputs) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    sent = user32.SendInput(len(inputs), ctypes.byref(inputs), ctypes.sizeof(inputs[0]))
    if sent != len(inputs):
        error = ctypes.get_last_error()
        raise RuntimeError(f"SendInput failed with Windows error {error}.")


def send_ctrl_v() -> None:
    input_cls, keybdinput_cls, input_keyboard = _keyboard_input_classes()
    keyeventf_keyup = 0x0002
    vk_control = 0x11
    vk_v = 0x56

    def key(vk: int, flags: int = 0):
        item = input_cls()
        item.type = input_keyboard
        item.union.ki = keybdinput_cls(vk, 0, flags, 0, 0)
        return item

    inputs = (input_cls * 4)(
        key(vk_control),
        key(vk_v),
        key(vk_v, keyeventf_keyup),
        key(vk_control, keyeventf_keyup),
    )
    _send_inputs(inputs)


def send_unicode_text(text: str, delay_ms: int = 1) -> None:
    input_cls, keybdinput_cls, input_keyboard = _keyboard_input_classes()
    keyeventf_keyup = 0x0002
    keyeventf_unicode = 0x0004
    units = utf16_units(text)
    chunk_size = 64

    for offset in range(0, len(units), chunk_size):
        chunk = units[offset : offset + chunk_size]

        def unicode_key(unit: int, flags: int):
            item = input_cls()
            item.type = input_keyboard
            item.union.ki = keybdinput_cls(0, unit, flags, 0, 0)
            return item

        raw_inputs = []
        for unit in chunk:
            raw_inputs.append(unicode_key(unit, keyeventf_unicode))
            raw_inputs.append(unicode_key(unit, keyeventf_unicode | keyeventf_keyup))
        inputs = (input_cls * len(raw_inputs))(*raw_inputs)
        _send_inputs(inputs)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000)


def _copy_failure_text(text: str, enabled: bool) -> bool:
    if not enabled:
        return False
    set_clipboard_text(text)
    return True


def _try_clipboard_paste(
    text: str,
    insertion_settings: dict,
    *,
    logger: logging.Logger,
) -> tuple[bool, str]:
    preserve_formats = bool(insertion_settings.get("preserve_clipboard_formats", True))
    restore_text = bool(insertion_settings.get("restore_clipboard_text", True))
    snapshot = snapshot_clipboard() if preserve_formats else ClipboardSnapshot(())
    previous_text = None if preserve_formats else get_clipboard_text() if restore_text else None

    set_clipboard_text(text)
    send_ctrl_v()
    time.sleep(0.25)

    if preserve_formats and snapshot.has_items:
        restore_clipboard_snapshot(snapshot, logger=logger)
    elif should_restore_text_clipboard(restore_text, previous_text, text):
        set_clipboard_text(previous_text or "")
    return True, "Inserted text with clipboard paste."


def insert_text(
    text: str,
    target_hwnd: int | None,
    insertion_settings: dict,
    *,
    logger: logging.Logger | None = None,
) -> InsertionResult:
    log = logger or logging.getLogger(__name__)
    if not text:
        return InsertionResult(False, False, "No text to insert.")

    mode = str(insertion_settings.get("mode", "auto")).lower()
    clipboard_fallback = bool(insertion_settings.get("clipboard_fallback", True))
    copy_on_failure = bool(insertion_settings.get("copy_on_failure", True))
    timeout_ms = int(insertion_settings.get("focus_restore_timeout_ms", 700))

    current_integrity = current_process_integrity_level()
    target_integrity = target_window_integrity_level(target_hwnd)
    if not can_inject_into_target(current_integrity, target_integrity):
        copied = _copy_failure_text(text, copy_on_failure)
        return InsertionResult(
            False,
            copied,
            (
                "Target appears elevated or protected; final text "
                f"{'is on the clipboard' if copied else 'was not inserted'}."
            ),
        )

    if not restore_focus(target_hwnd, timeout_ms, logger=log):
        copied = _copy_failure_text(text, copy_on_failure)
        return InsertionResult(
            False,
            copied,
            f"Could not restore target focus; final text {'is on the clipboard' if copied else 'was not inserted'}.",
        )

    direct_delay = int(insertion_settings.get("direct_typing_delay_ms", 1))
    if mode in {"auto", "direct", "typing"}:
        try:
            send_unicode_text(text, direct_delay)
            return InsertionResult(True, False, "Inserted text with direct Unicode typing.")
        except Exception as exc:
            log.warning("Direct typing failed: %s", exc)
            if mode in {"direct", "typing"} and not clipboard_fallback:
                copied = _copy_failure_text(text, copy_on_failure)
                return InsertionResult(
                    False,
                    copied,
                    f"Direct typing failed; final text {'is on the clipboard' if copied else 'was not inserted'}.",
                )

    if mode in {"auto", "clipboard"} and clipboard_fallback:
        try:
            _ok, message = _try_clipboard_paste(text, insertion_settings, logger=log)
            return InsertionResult(True, False, message)
        except Exception as exc:
            copied = _copy_failure_text(text, copy_on_failure)
            return InsertionResult(
                False,
                copied,
                f"Clipboard paste failed; final text {'is on the clipboard' if copied else 'was not inserted'}: {exc}",
            )

    copied = _copy_failure_text(text, copy_on_failure)
    return InsertionResult(
        False,
        copied,
        f"No supported insertion path succeeded; final text {'is on the clipboard' if copied else 'was not inserted'}.",
    )
