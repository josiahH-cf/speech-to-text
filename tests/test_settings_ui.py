import pytest

from local_dictation.config import default_settings
from local_dictation.settings_ui import _updated_settings


def test_updated_settings_normalizes_and_preserves_original_settings():
    settings = default_settings()

    updated = _updated_settings(
        settings,
        hotkey="Ctrl-Alt-Space",
        stt_model="tiny.en",
        cleanup_enabled=True,
        cleanup_model="gemma3:1b",
        insertion_mode="DIRECT",
        input_device_id="default",
        cue_tone="low_chime",
        gain_db="3",
        silence_enabled=False,
        silence_seconds="2.5",
        speech_threshold="0.02",
        startup_enabled=True,
    )

    assert updated["hotkey"] == "ctrl+alt+space"
    assert updated["stt"]["model"] == "tiny.en"
    assert updated["cleanup"]["enabled"] is True
    assert updated["insertion"]["mode"] == "direct"
    assert updated["recording"]["input_device_id"] is None
    assert updated["recording"]["cue_tone"] == "low_chime"
    assert updated["recording"]["gain_db"] == 3.0
    assert updated["recording"]["silence_stop"]["enabled"] is False
    assert updated["recording"]["silence_stop"]["silence_seconds"] == 2.5
    assert updated["recording"]["silence_stop"]["speech_threshold"] == 0.02
    assert updated["startup"]["enabled"] is True
    assert settings["stt"]["model"] == "base.en"


def test_updated_settings_rejects_invalid_hotkey():
    with pytest.raises(ValueError, match="Unsupported hotkey"):
        _updated_settings(
            default_settings(),
            hotkey="ctrl+alt+notakey",
            stt_model="base.en",
            cleanup_enabled=False,
            cleanup_model="gemma3:1b",
            insertion_mode="auto",
            silence_enabled=True,
            silence_seconds="1.4",
            speech_threshold="0.012",
            startup_enabled=False,
        )


def test_updated_settings_rejects_non_positive_silence_values():
    with pytest.raises(ValueError, match="Silence seconds must be greater than 0"):
        _updated_settings(
            default_settings(),
            hotkey="ctrl+alt+space",
            stt_model="base.en",
            cleanup_enabled=False,
            cleanup_model="gemma3:1b",
            insertion_mode="auto",
            silence_enabled=True,
            silence_seconds="0",
            speech_threshold="0.012",
            startup_enabled=False,
        )


def test_updated_settings_rejects_unsupported_insertion_mode():
    with pytest.raises(ValueError, match="Insertion mode"):
        _updated_settings(
            default_settings(),
            hotkey="ctrl+alt+space",
            stt_model="base.en",
            cleanup_enabled=False,
            cleanup_model="gemma3:1b",
            insertion_mode="telepathy",
            silence_enabled=True,
            silence_seconds="1.4",
            speech_threshold="0.012",
            startup_enabled=False,
        )


def test_updated_settings_rejects_unsupported_recording_cue():
    with pytest.raises(ValueError, match="Recording cue"):
        _updated_settings(
            default_settings(),
            hotkey="ctrl+alt+space",
            stt_model="base.en",
            cleanup_enabled=False,
            cleanup_model="gemma3:1b",
            insertion_mode="auto",
            cue_tone="loud_bell",
            silence_enabled=True,
            silence_seconds="1.4",
            speech_threshold="0.012",
            startup_enabled=False,
        )