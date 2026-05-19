import pytest
import threading
from types import SimpleNamespace

from local_dictation.hotkey import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    GlobalHotkeyListener,
    HotkeyError,
    _hotkey_message_values,
    parse_hotkey,
)


def test_parse_default_hotkey():
    binding = parse_hotkey("ctrl+alt+space")

    assert binding.vk == 0x20
    assert binding.modifiers & MOD_CONTROL
    assert binding.modifiers & MOD_ALT
    assert binding.modifiers & MOD_NOREPEAT
    assert binding.normalized == "ctrl+alt+space"


def test_rejects_unknown_key():
    with pytest.raises(HotkeyError):
        parse_hotkey("ctrl+alt+notakey")


def test_rejects_reserved_f12():
    with pytest.raises(HotkeyError):
        parse_hotkey("ctrl+f12")


def test_listener_stop_does_not_join_current_thread():
    listener = GlobalHotkeyListener("ctrl+alt+space", lambda: None)
    listener._thread = threading.current_thread()

    listener.stop()


def test_hotkey_message_values_supports_pymsg_object_shape():
    message = SimpleNamespace(message=0x0312, wParam=1)

    assert _hotkey_message_values(message) == (0x0312, 1)


def test_hotkey_message_values_supports_tuple_shape():
    message = (None, 0x0312, 1, 0, 0, (0, 0))

    assert _hotkey_message_values(message) == (0x0312, 1)
