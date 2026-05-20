from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RecordingResult:
    audio: object
    sample_rate: int
    duration_seconds: float


class RecordingError(RuntimeError):
    """Raised when microphone capture fails."""


def gain_multiplier(gain_db: float) -> float:
    return 10 ** (float(gain_db) / 20)


def apply_gain(audio, gain_db: float, *, np_module=None):
    if float(gain_db) == 0:
        return audio
    if np_module is None:
        import numpy as np_module

    return np_module.clip(audio * gain_multiplier(gain_db), -1.0, 1.0)


def parse_input_device_id(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() == "default":
            return None
        value = text.split(":", 1)[0].strip()
    return int(value)


def should_stop_for_silence(
    *,
    enabled: bool,
    has_speech: bool,
    elapsed_seconds: float,
    silence_elapsed_seconds: float,
    min_recording_seconds: float,
    silence_seconds: float,
) -> bool:
    return bool(
        enabled
        and has_speech
        and elapsed_seconds >= min_recording_seconds
        and silence_elapsed_seconds >= silence_seconds
    )


class MicrophoneRecorder:
    def __init__(
        self,
        recording_settings: dict,
        *,
        logger: logging.Logger | None = None,
        on_max_duration: Callable[[], None] | None = None,
        on_silence_stop: Callable[[], None] | None = None,
    ) -> None:
        self.sample_rate = int(recording_settings.get("sample_rate", 16000))
        self.channels = int(recording_settings.get("channels", 1))
        self.max_seconds = float(recording_settings.get("max_seconds", 120))
        self.input_device_id = parse_input_device_id(recording_settings.get("input_device_id"))
        self.gain_db = float(recording_settings.get("gain_db", 0.0))
        silence_settings = recording_settings.get("silence_stop", {})
        self.silence_enabled = bool(silence_settings.get("enabled", True))
        self.min_recording_seconds = float(silence_settings.get("min_recording_seconds", 1.5))
        self.speech_threshold = float(silence_settings.get("speech_threshold", 0.012))
        self.silence_seconds = float(silence_settings.get("silence_seconds", 1.4))
        self.logger = logger or logging.getLogger(__name__)
        self.on_max_duration = on_max_duration
        self.on_silence_stop = on_silence_stop
        self._frames: list[object] = []
        self._stream = None
        self._timer: threading.Timer | None = None
        self._started_at = 0.0
        self._last_speech_at = 0.0
        self._has_speech = False
        self._silence_stop_requested = False
        self._lock = threading.Lock()

    def start(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise RecordingError("sounddevice or numpy is not installed.") from exc

        def callback(indata, frames, time_info, status) -> None:
            if status:
                self.logger.warning("Microphone stream status: %s", status)
            now = time.monotonic()
            with self._lock:
                adjusted = apply_gain(indata, self.gain_db, np_module=np)
                self._frames.append(adjusted.copy())
                elapsed = now - self._started_at if self._started_at else 0.0
                rms = float(np.sqrt(np.mean(np.square(adjusted)))) if getattr(adjusted, "size", 0) else 0.0
                if rms >= self.speech_threshold:
                    self._has_speech = True
                    self._last_speech_at = now
                silence_elapsed = now - self._last_speech_at if self._last_speech_at else 0.0
                should_stop = should_stop_for_silence(
                    enabled=self.silence_enabled,
                    has_speech=self._has_speech,
                    elapsed_seconds=elapsed,
                    silence_elapsed_seconds=silence_elapsed,
                    min_recording_seconds=self.min_recording_seconds,
                    silence_seconds=self.silence_seconds,
                )
                if should_stop and not self._silence_stop_requested and self.on_silence_stop:
                    self._silence_stop_requested = True
                    threading.Thread(target=self.on_silence_stop, name="silence-stop", daemon=True).start()

        try:
            self._frames = []
            self._has_speech = False
            self._last_speech_at = 0.0
            self._silence_stop_requested = False
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=self.input_device_id,
                callback=callback,
            )
            self._stream.start()
            self._started_at = time.monotonic()
            if self.max_seconds > 0 and self.on_max_duration:
                self._timer = threading.Timer(self.max_seconds, self.on_max_duration)
                self._timer.daemon = True
                self._timer.start()
        except Exception as exc:
            raise RecordingError(f"Could not start microphone recording: {exc}") from exc

    def stop(self) -> RecordingResult:
        try:
            import numpy as np
        except ImportError as exc:
            raise RecordingError("numpy is not installed.") from exc

        if self._timer:
            self._timer.cancel()
            self._timer = None

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:
                self.logger.warning("Could not cleanly stop microphone stream: %s", exc)
            finally:
                self._stream = None

        with self._lock:
            frames = list(self._frames)
            self._frames = []

        if frames:
            audio = np.concatenate(frames, axis=0)
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
        else:
            audio = np.array([], dtype=np.float32)

        duration = max(0.0, time.monotonic() - self._started_at) if self._started_at else 0.0
        return RecordingResult(audio=audio.astype("float32", copy=False), sample_rate=self.sample_rate, duration_seconds=duration)
