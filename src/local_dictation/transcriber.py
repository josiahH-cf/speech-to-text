from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .recorder import RecordingResult


class TranscriptionError(RuntimeError):
    """Raised when local transcription fails."""


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None
    duration_seconds: float


class FasterWhisperTranscriber:
    def __init__(self, stt_settings: dict, *, logger: logging.Logger | None = None) -> None:
        self.settings = stt_settings
        self.logger = logger or logging.getLogger(__name__)
        self._model: Any | None = None

    def load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise TranscriptionError(
                "Could not import faster-whisper. The package may be missing, corrupted, "
                f"or blocked by Windows Application Control or antivirus policy: {exc}"
            ) from exc

        model_name = self.settings.get("model", "base.en")
        self.logger.info("Loading faster-whisper model %s", model_name)
        try:
            self._model = WhisperModel(
                model_name,
                device=self.settings.get("device", "cpu"),
                compute_type=self.settings.get("compute_type", "int8"),
                local_files_only=bool(self.settings.get("local_files_only", False)),
            )
        except Exception as exc:
            raise TranscriptionError(f"Could not load faster-whisper model {model_name}: {exc}") from exc
        return self._model

    def download_model(self) -> None:
        self.load_model()

    def transcribe(self, recording: RecordingResult) -> TranscriptionResult:
        try:
            import numpy as np
        except ImportError as exc:
            raise TranscriptionError("numpy is not installed.") from exc

        audio = recording.audio
        if getattr(audio, "size", 0) == 0:
            return TranscriptionResult(text="", language=None, duration_seconds=recording.duration_seconds)

        if recording.sample_rate != 16000:
            self.logger.warning(
                "Recording sample rate is %s Hz; faster-whisper expects 16 kHz arrays.",
                recording.sample_rate,
            )

        audio_array = np.asarray(audio, dtype="float32")
        model = self.load_model()
        language = self.settings.get("language") or None

        try:
            segments, info = model.transcribe(
                audio_array,
                language=language,
                vad_filter=bool(self.settings.get("vad_filter", True)),
                beam_size=5,
            )
            text = "".join(segment.text for segment in segments).strip()
            detected_language = getattr(info, "language", language)
        except Exception as exc:
            raise TranscriptionError(f"Transcription failed: {exc}") from exc

        return TranscriptionResult(
            text=text,
            language=detected_language,
            duration_seconds=recording.duration_seconds,
        )
