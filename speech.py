"""Speech input/output manager for voice features."""

import threading

import pyttsx3
import speech_recognition as sr


class SpeechManager:
    """Handles one-shot listening and async text-to-speech."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self._engine = pyttsx3.init()
        self._speak_lock = threading.Lock()

    def listen(self) -> str:
        """Listen once and return recognized text or an empty string."""
        try:
            with sr.Microphone() as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
            return self.recognizer.recognize_google(audio).strip()
        except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError, OSError):
            return ""
        except Exception:
            return ""

    def speak(self, text: str) -> None:
        """Speak text asynchronously so UI remains responsive."""
        cleaned = (text or "").strip()
        if not cleaned:
            return

        threading.Thread(
            target=self._speak_worker,
            args=(cleaned,),
            daemon=True,
        ).start()

    def _speak_worker(self, text: str) -> None:
        with self._speak_lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                return
