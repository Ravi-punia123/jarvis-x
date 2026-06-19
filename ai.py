"""Ollama integration for generating responses."""

from ollama import chat

from config import MODEL_NAME, SYSTEM_PROMPT
from memory import MemoryManager


class OllamaAssistant:
    """Wraps the Ollama API so the UI does not talk to the model directly."""

    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name

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
        """Yield response text incrementally as Ollama streams it."""
        messages = self._build_messages(user_text, memory)

        for chunk in chat(
            model=self.model_name,
            messages=messages,
            stream=True,
        ):
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
