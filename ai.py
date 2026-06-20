"""Ollama integration for generating responses."""

import traceback
from ollama import chat, RequestError
import urllib.request
from config import MODEL_NAME, SYSTEM_PROMPT
from memory import MemoryManager
from logger import get_logger

_log = get_logger("ai")


class OllamaAssistant:
    """Wraps the Ollama API so the UI does not talk to the model directly."""

    def __init__(self, model_name: str = MODEL_NAME, url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.temperature = 0.2
        self.context_length = 8192
        self.ollama_url = url

    def configure(self, model_name: str | None = None, temperature: float | None = None, context_length: int | None = None, url: str | None = None):
        if model_name:
            self.model_name = model_name
        if temperature is not None:
            self.temperature = float(temperature)
        if context_length is not None:
            self.context_length = int(context_length)
        if url:
            self.ollama_url = url

    def is_online(self) -> bool:
        """Check if the local Ollama server is running and reachable."""
        try:
            with urllib.request.urlopen(self.ollama_url, timeout=2.0) as conn:
                return conn.status == 200
        except Exception:
            return False

    def check_model_available(self) -> bool:
        """Check if the configured model is pulled and available."""
        try:
            import json
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as conn:
                data = json.loads(conn.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", [])]
                # Check for direct match or tagless match
                return self.model_name in models or any(m.startswith(self.model_name + ":") for m in models)
        except Exception:
            return False

    def _build_messages(self, user_text: str, memory: MemoryManager):
        history_data = memory.get_recent_history(limit=100)
        history = [
            {"role": item.get("role"), "content": item.get("content")}
            for item in history_data["messages"]
        ]
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)

        if (
            not history
            or history[-1].get("role") != "user"
            or history[-1].get("content") != user_text
        ):
            messages.append({"role": "user", "content": user_text})

        return messages

    def stream_response(self, user_text: str, memory: MemoryManager):
        """Yield response text incrementally as Ollama streams it, with auto-retry and safety fallback."""
        if not self.is_online():
            _log.error("Ollama server is offline at %s", self.ollama_url)
            raise ConnectionError(f"Ollama server is offline. Please make sure Ollama is running at {self.ollama_url}")

        messages = self._build_messages(user_text, memory)
        
        # We try with the configured context size first, and fall back to a smaller context if it crashes (500)
        ctx_options = [self.context_length, 2048]
        last_err = None

        for attempt, ctx in enumerate(ctx_options, 1):
            try:
                _log.info("Attempting inference with model=%s, context=%d (attempt=%d)", self.model_name, ctx, attempt)
                for chunk in chat(
                    model=self.model_name,
                    messages=messages,
                    stream=True,
                    options={"temperature": self.temperature, "num_ctx": ctx},
                ):
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                # If we successfully finish streaming, return
                return
            except Exception as e:
                last_err = e
                _log.error("Inference attempt %d failed with context=%d: %s", attempt, ctx, str(e))
                _log.error("Traceback: %s", traceback.format_exc())
                if attempt < len(ctx_options):
                    _log.info("Retrying with fallback context size = 2048")
                    continue
        
        # If all attempts fail, raise the last exception
        raise last_err
