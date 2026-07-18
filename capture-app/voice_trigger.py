from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import Callable


class VoiceTriggerService:
    """Background listener that triggers a callback when the word 'next' is detected."""

    def __init__(
        self,
        model_path: Path,
        trigger_word: str,
        on_trigger: Callable[[], None],
        on_status: Callable[[str], None],
    ) -> None:
        self.model_path = model_path
        self.trigger_word = trigger_word.lower().strip()
        self.on_trigger = on_trigger
        self.on_status = on_status
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except ImportError:
            self.on_status("Voice: missing dependencies (install sounddevice + vosk)")
            return

        if not self.model_path.exists():
            self.on_status(f"Voice: model missing at {self.model_path}")
            return

        self.on_status("Voice: loading model...")

        try:
            model = Model(str(self.model_path))
            recognizer = KaldiRecognizer(model, 16000)
        except Exception as exc:  # pragma: no cover - depends on local model state
            self.on_status(f"Voice: model load failed ({exc})")
            return

        audio_queue: queue.Queue[bytes] = queue.Queue()

        def _audio_callback(indata, _frames, _time, status) -> None:
            if status:
                return
            audio_queue.put(bytes(indata))

        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=_audio_callback,
            ):
                self.on_status("Voice: listening for 'next'")
                while not self._stop_event.is_set():
                    try:
                        data = audio_queue.get(timeout=0.25)
                    except queue.Empty:
                        continue

                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result() or "{}")
                        text = str(result.get("text", "")).lower()
                        if self._contains_trigger(text):
                            self.on_status("Voice: trigger detected")
                            self.on_trigger()
        except Exception as exc:  # pragma: no cover - hardware/runtime dependent
            self.on_status(f"Voice: stopped ({exc})")
            return

        self.on_status("Voice: stopped")

    def _contains_trigger(self, text: str) -> bool:
        if not text:
            return False
        words = text.split()
        return self.trigger_word in words or self.trigger_word in text

