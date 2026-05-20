from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum

from .cleanup import cleanup_text
from .config import load_settings, settings_path
from .hotkey import GlobalHotkeyListener
from .insertion import capture_foreground_window, insert_text
from .logging_config import get_logger
from .recorder import MicrophoneRecorder, RecordingError
from .transcriber import FasterWhisperTranscriber, TranscriptionError


class AppState(str, Enum):
    IDLE = "IDLE"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"


@dataclass(frozen=True)
class RuntimeControlResult:
    ok: bool
    message: str


class DictationApp:
    def __init__(self, settings: dict, *, logger: logging.Logger | None = None) -> None:
        self.settings = settings
        self.logger = logger or get_logger("app")
        self.state = AppState.IDLE
        self._lock = threading.RLock()
        self._hotkey: GlobalHotkeyListener | None = None
        self._recorder: MicrophoneRecorder | None = None
        self._target_hwnd: int | None = None
        self._transcriber = FasterWhisperTranscriber(settings.get("stt", {}), logger=get_logger("transcriber"))
        self.last_transcript = ""
        self._reload_stop = threading.Event()
        self._reload_thread: threading.Thread | None = None
        self._settings_mtime = self._current_settings_mtime()
        self._pending_hotkey_reregister = False
        self._started = False
        self._runtime_enabled = False

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._reload_stop.clear()
            self._started = True
            self._runtime_enabled = True
            self._start_hotkey_locked()
            self._reload_thread = threading.Thread(target=self._reload_loop, name="settings-reload", daemon=True)
            self._reload_thread.start()
        self.logger.info("Local Dictation app started.")

    def stop(self) -> None:
        self._reload_stop.set()
        with self._lock:
            recorder = self._recorder
            self._recorder = None
            self.state = AppState.IDLE
            self._runtime_enabled = False
            self._started = False
            self._pending_hotkey_reregister = False
        if recorder:
            try:
                recorder.stop()
            except Exception:
                self.logger.debug("Recorder cleanup failed during app stop.", exc_info=True)
        if self._hotkey:
            self._hotkey.stop()
            self._hotkey = None
        if self._reload_thread:
            self._reload_thread.join(timeout=2)
            self._reload_thread = None
        self.logger.info("Local Dictation app stopped.")

    def runtime_enabled(self) -> bool:
        with self._lock:
            return self._runtime_enabled

    def enable_runtime(self) -> RuntimeControlResult:
        with self._lock:
            if self._runtime_enabled:
                return RuntimeControlResult(True, "Dictation runtime is already enabled.")
            self.reload_settings()
            self._runtime_enabled = True
            self._start_hotkey_locked()
        self.logger.info("Dictation runtime enabled.")
        return RuntimeControlResult(True, "Dictation runtime enabled.")

    def disable_runtime(self) -> RuntimeControlResult:
        with self._lock:
            if not self._runtime_enabled:
                return RuntimeControlResult(True, "Dictation runtime is already disabled.")
            if self.state != AppState.IDLE:
                return RuntimeControlResult(False, f"Dictation runtime is busy: {self.state.value}.")
            hotkey = self._hotkey
            self._hotkey = None
            self._runtime_enabled = False
            self._pending_hotkey_reregister = False
        if hotkey:
            hotkey.stop()
        self.logger.info("Dictation runtime disabled.")
        return RuntimeControlResult(True, "Dictation runtime disabled.")

    def status_text(self) -> str:
        with self._lock:
            return self.state.value

    def handle_hotkey(self) -> None:
        with self._lock:
            if not self._runtime_enabled:
                self.logger.info("Hotkey ignored while dictation runtime is disabled.")
                return
            if self.state == AppState.IDLE:
                self.reload_settings()
                self._start_recording_locked()
                return
            if self.state == AppState.RECORDING:
                self._begin_processing_locked("hotkey")
                return
            self.logger.info("Hotkey ignored while processing current recording.")

    def _start_recording_locked(self) -> None:
        self._target_hwnd = capture_foreground_window()
        recorder = MicrophoneRecorder(
            self.settings.get("recording", {}),
            logger=get_logger("recorder"),
            on_max_duration=self._max_duration_reached,
            on_silence_stop=self._silence_stop_reached,
        )
        try:
            recorder.start()
        except RecordingError as exc:
            self.logger.error("Recording could not start: %s", exc)
            self.state = AppState.IDLE
            self._target_hwnd = None
            return

        self._recorder = recorder
        self.state = AppState.RECORDING
        self.logger.info("Recording started. Target hwnd=%s", self._target_hwnd)

    def _begin_processing_locked(self, reason: str) -> None:
        recorder = self._recorder
        target_hwnd = self._target_hwnd
        self._recorder = None
        self._target_hwnd = None
        self.state = AppState.PROCESSING
        self.logger.info("Recording stop requested by %s.", reason)
        worker = threading.Thread(
            target=self._process_recording,
            args=(recorder, target_hwnd),
            name="dictation-processing",
            daemon=True,
        )
        worker.start()

    def _max_duration_reached(self) -> None:
        with self._lock:
            if self.state == AppState.RECORDING:
                self._begin_processing_locked("max duration")

    def _silence_stop_reached(self) -> None:
        with self._lock:
            if self.state == AppState.RECORDING:
                self._begin_processing_locked("silence")

    def _start_hotkey_locked(self) -> None:
        if self._hotkey is not None:
            return
        self._hotkey = GlobalHotkeyListener(
            self.settings.get("hotkey", "ctrl+alt+space"),
            self.handle_hotkey,
            logger=get_logger("hotkey"),
        )
        self._hotkey.start()

    def _current_settings_mtime(self) -> float:
        try:
            return settings_path().stat().st_mtime
        except OSError:
            return 0.0

    def _reload_loop(self) -> None:
        while not self._reload_stop.wait(2):
            try:
                if self._current_settings_mtime() != self._settings_mtime:
                    self.reload_settings()
            except Exception:
                self.logger.debug("Settings reload check failed.", exc_info=True)

    def reload_settings(self, *, force: bool = False) -> None:
        with self._lock:
            new_mtime = self._current_settings_mtime()
            if not force and new_mtime == self._settings_mtime:
                return
            old_hotkey = self.settings.get("hotkey")
            old_stt = self.settings.get("stt", {})
            new_settings = load_settings(create=True)
            self.settings = new_settings
            self._settings_mtime = new_mtime or time.monotonic()

            if new_settings.get("stt", {}) != old_stt:
                self._transcriber = FasterWhisperTranscriber(
                    new_settings.get("stt", {}),
                    logger=get_logger("transcriber"),
                )

            hotkey_changed = new_settings.get("hotkey") != old_hotkey
            if hotkey_changed and not self._runtime_enabled:
                self._pending_hotkey_reregister = False
            elif hotkey_changed and self.state == AppState.IDLE and self._hotkey and not self._hotkey.is_listener_thread():
                self.logger.info("Hotkey changed; re-registering global hotkey.")
                self._reregister_hotkey_locked()
            elif hotkey_changed:
                self._pending_hotkey_reregister = True
                self.logger.info("Hotkey changed; re-registration deferred until idle.")

    def _reregister_hotkey_locked(self) -> None:
        if self._hotkey:
            self._hotkey.stop()
            self._hotkey = None
        if self._runtime_enabled:
            self._start_hotkey_locked()
        self._pending_hotkey_reregister = False

    def _apply_pending_hotkey_reregister_locked(self) -> None:
        if self._runtime_enabled and self._pending_hotkey_reregister and self.state == AppState.IDLE:
            self.logger.info("Applying deferred hotkey re-registration.")
            self._reregister_hotkey_locked()

    def _process_recording(self, recorder: MicrophoneRecorder | None, target_hwnd: int | None) -> None:
        try:
            if recorder is None:
                self.logger.warning("No recorder was available for processing.")
                return

            recording = recorder.stop()
            self.logger.info(
                "Recording stopped: %.2f seconds.",
                recording.duration_seconds,
            )

            result = self._transcriber.transcribe(recording)
            transcript = result.text.strip()
            if not transcript:
                self.logger.warning("Transcription returned no text.")
                return

            self.logger.info("Transcription completed with %d characters.", len(transcript))
            final_text = cleanup_text(transcript, self.settings.get("cleanup", {}), logger=get_logger("cleanup"))
            self.last_transcript = final_text
            insertion = insert_text(
                final_text,
                target_hwnd,
                self.settings.get("insertion", {}),
                logger=get_logger("insertion"),
            )
            if insertion.inserted:
                self.logger.info(insertion.message)
            else:
                self.logger.warning(insertion.message)
        except TranscriptionError as exc:
            self.logger.error("Transcription failed: %s", exc)
        except Exception:
            self.logger.exception("Unexpected processing failure.")
        finally:
            with self._lock:
                self.state = AppState.IDLE
                self._apply_pending_hotkey_reregister_locked()
