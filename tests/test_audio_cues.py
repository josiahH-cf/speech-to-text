import pytest

from local_dictation.audio_cues import _cue_wave_bytes, play_recording_cue, selected_cue_tone


def test_selected_cue_tone_defaults_invalid_values_to_off():
    assert selected_cue_tone({}) == "off"
    assert selected_cue_tone({"cue_tone": " LOW_CHIME "}) == "low_chime"
    assert selected_cue_tone({"cue_tone": "loud_bell"}) == "off"


def test_off_cue_does_not_prepare_or_play_audio(monkeypatch):
    monkeypatch.setattr("local_dictation.audio_cues._cue_wave_bytes", lambda *_args: pytest.fail("off should not build audio"))

    play_recording_cue({"cue_tone": "off"}, "start")


def test_built_in_cues_are_generated_as_wav_bytes():
    data = _cue_wave_bytes("muted_tick", "start")

    assert data.startswith(b"RIFF")
    assert b"WAVE" in data[:16]