from local_dictation.recorder import should_stop_for_silence


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
