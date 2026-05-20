import numpy as np

from local_dictation.recorder import apply_gain, gain_multiplier, parse_input_device_id, should_stop_for_silence


def test_gain_multiplier_uses_decibels():
    assert round(gain_multiplier(6), 2) == 2.0


def test_apply_gain_boosts_and_clips_audio():
    audio = np.array([0.25, -0.75], dtype=np.float32)

    adjusted = apply_gain(audio, 12)

    assert adjusted.dtype == np.float32
    assert adjusted[0] > audio[0]
    assert adjusted[1] == -1.0


def test_parse_input_device_id_accepts_default_and_numeric_labels():
    assert parse_input_device_id(None) is None
    assert parse_input_device_id("default") is None
    assert parse_input_device_id("3: USB Microphone") == 3


def test_silence_stop_requires_speech_and_minimum_duration():
    assert (
        should_stop_for_silence(
            enabled=True,
            has_speech=False,
            elapsed_seconds=10,
            silence_elapsed_seconds=10,
            min_recording_seconds=1.5,
            silence_seconds=1.4,
        )
        is False
    )
    assert (
        should_stop_for_silence(
            enabled=True,
            has_speech=True,
            elapsed_seconds=1.0,
            silence_elapsed_seconds=2.0,
            min_recording_seconds=1.5,
            silence_seconds=1.4,
        )
        is False
    )


def test_silence_stop_allows_speech_before_minimum_then_stops_later():
    assert (
        should_stop_for_silence(
            enabled=True,
            has_speech=True,
            elapsed_seconds=2.0,
            silence_elapsed_seconds=1.5,
            min_recording_seconds=1.5,
            silence_seconds=1.4,
        )
        is True
    )


def test_silence_stop_triggers_after_threshold():
    assert (
        should_stop_for_silence(
            enabled=True,
            has_speech=True,
            elapsed_seconds=3.0,
            silence_elapsed_seconds=1.5,
            min_recording_seconds=1.5,
            silence_seconds=1.4,
        )
        is True
    )
