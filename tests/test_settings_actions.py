import pytest

from local_dictation.config import default_settings
from local_dictation.settings_actions import update_core_settings, update_settings


def test_update_core_settings_normalizes_hotkey_and_preserves_unrelated_settings():
    settings = default_settings()
    settings["custom"] = {"keep": True}

    updated = update_core_settings(
        settings,
        hotkey="Ctrl-Alt-Space",
        stt_model="tiny.en",
        cleanup_enabled=True,
        cleanup_model="gemma3:1b",
    )

    assert updated["hotkey"] == "ctrl+alt+space"
    assert updated["stt"]["model"] == "tiny.en"
    assert updated["cleanup"]["enabled"] is True
    assert updated["cleanup"]["model"] == "gemma3:1b"
    assert updated["custom"] == {"keep": True}
    assert settings["stt"]["model"] == "base.en"


def test_update_core_settings_rejects_invalid_hotkey():
    with pytest.raises(ValueError, match="Unsupported hotkey"):
        update_core_settings(
            default_settings(),
            hotkey="ctrl+alt+nope",
            stt_model="base.en",
            cleanup_enabled=False,
            cleanup_model="gemma3:1b",
        )


def test_update_settings_keeps_existing_settings_ui_behavior():
    updated = update_settings(
        default_settings(),
        hotkey="ctrl+alt+space",
        stt_model="small.en",
        cleanup_enabled=False,
        cleanup_model="gemma3:1b",
        insertion_mode="DIRECT",
        input_device_id="3: USB Microphone",
        gain_db="6",
        silence_enabled=False,
        silence_seconds="2.0",
        speech_threshold="0.02",
        startup_enabled=True,
    )

    assert updated["stt"]["model"] == "small.en"
    assert updated["insertion"]["mode"] == "direct"
    assert updated["recording"]["input_device_id"] == 3
    assert updated["recording"]["gain_db"] == 6.0
    assert updated["recording"]["silence_stop"]["enabled"] is False
    assert updated["recording"]["silence_stop"]["silence_seconds"] == 2.0
    assert updated["recording"]["silence_stop"]["speech_threshold"] == 0.02
    assert updated["startup"]["enabled"] is True


def test_update_settings_rejects_invalid_gain_and_device():
    with pytest.raises(ValueError, match="Microphone gain"):
        update_settings(
            default_settings(),
            hotkey="ctrl+alt+space",
            stt_model="base.en",
            cleanup_enabled=False,
            cleanup_model="gemma3:1b",
            insertion_mode="auto",
            input_device_id="default",
            gain_db="40",
            silence_enabled=True,
            silence_seconds="1.4",
            speech_threshold="0.012",
            startup_enabled=False,
        )

    with pytest.raises(ValueError, match="Input device"):
        update_settings(
            default_settings(),
            hotkey="ctrl+alt+space",
            stt_model="base.en",
            cleanup_enabled=False,
            cleanup_model="gemma3:1b",
            insertion_mode="auto",
            input_device_id="microphone",
            gain_db="0",
            silence_enabled=True,
            silence_seconds="1.4",
            speech_threshold="0.012",
            startup_enabled=False,
        )