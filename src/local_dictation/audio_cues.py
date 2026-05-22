from __future__ import annotations

import io
import logging
import math
import struct
import threading
import wave
from functools import lru_cache
from typing import Literal

CUE_TONE_OPTIONS = ("off", "soft_ding", "low_chime", "muted_tick")
CueEvent = Literal["start", "stop"]

_SAMPLE_RATE = 22050
_AMPLITUDE = 0.08
_GAP_MS = 12

_TONE_SPECS: dict[str, dict[CueEvent, tuple[tuple[float, int], ...]]] = {
    "soft_ding": {
        "start": ((660.0, 70), (880.0, 90)),
        "stop": ((880.0, 60), (660.0, 100)),
    },
    "low_chime": {
        "start": ((392.0, 90), (523.25, 110)),
        "stop": ((523.25, 80), (392.0, 120)),
    },
    "muted_tick": {
        "start": ((880.0, 45),),
        "stop": ((660.0, 45),),
    },
}


def selected_cue_tone(recording_settings: dict) -> str:
    tone = str(recording_settings.get("cue_tone", "off")).strip().lower()
    return tone if tone in CUE_TONE_OPTIONS else "off"


def play_recording_cue(recording_settings: dict, event: CueEvent, *, logger: logging.Logger | None = None) -> None:
    tone = selected_cue_tone(recording_settings)
    if tone == "off":
        return
    log = logger or logging.getLogger(__name__)
    thread = threading.Thread(
        target=_play_winsound,
        args=(_cue_wave_bytes(tone, event), log),
        name=f"recording-cue-{event}",
        daemon=True,
    )
    thread.start()


def _play_winsound(wave_bytes: bytes, logger: logging.Logger) -> None:
    try:
        import winsound

        winsound.PlaySound(wave_bytes, winsound.SND_MEMORY)
    except Exception:
        logger.debug("Recording cue playback failed.", exc_info=True)


@lru_cache(maxsize=None)
def _cue_wave_bytes(tone: str, event: CueEvent) -> bytes:
    notes = _TONE_SPECS[tone][event]
    frames = bytearray()
    for note_index, (frequency, duration_ms) in enumerate(notes):
        if note_index:
            frames.extend(b"\x00\x00" * int(_SAMPLE_RATE * _GAP_MS / 1000))
        frames.extend(_note_frames(frequency, duration_ms))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(_SAMPLE_RATE)
        handle.writeframes(bytes(frames))
    return buffer.getvalue()


def _note_frames(frequency: float, duration_ms: int) -> bytes:
    frame_count = max(1, int(_SAMPLE_RATE * duration_ms / 1000))
    frames = bytearray()
    for sample_index in range(frame_count):
        position = sample_index / frame_count
        envelope = min(1.0, position / 0.18, (1.0 - position) / 0.28)
        sample = math.sin(2.0 * math.pi * frequency * sample_index / _SAMPLE_RATE)
        value = int(sample * envelope * _AMPLITUDE * 32767)
        frames.extend(struct.pack("<h", value))
    return bytes(frames)