"""Hands-free background speech continuous wake listener."""

import time
import threading
from typing import Callable, Optional
from speech import SpeechManager
from logger import get_logger

_log = get_logger("os_voice")


class VoiceWakeListener:
    """Listens continuously on the default audio input channel for 'Hey Jarvis' or 'Jarvis'."""

    def __init__(self, speech: SpeechManager, trigger_callback: Callable[[str], None]):
        self.speech = speech
        self.trigger_callback = trigger_callback
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        # Prevent starting if pyaudio isn't fully compiled or installed under 3.14
        try:
            try:
                import pyaudio
            except ImportError:
                import pyaudiowpatch as pyaudio
        except ImportError:
            _log.warning("PyAudio not available. Background wake word listening disabled.")
            return

        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        _log.info("Voice wake listener daemon started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        _log.info("Voice wake listener daemon stopped")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                # Use SpeechManager to grab a short segment
                text = self.speech.listen()
                if text:
                    cleaned = text.strip().lower()
                    if "hey jarvis" in cleaned or "jarvis" in cleaned:
                        _log.info("Wake word detected: %s", text)
                        self.trigger_callback(text)
            except Exception as e:
                # Silent catch during mic unavailability
                pass
            time.sleep(0.5)
