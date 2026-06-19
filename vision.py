"""Vision module for screen capture and local model analysis."""

import json
import multiprocessing
import subprocess
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Dict

from ollama import chat, list as ollama_list, show as ollama_show

from config import MODEL_NAME


def _chat_worker(model_name: str, prompt: str, image_path: str, queue: multiprocessing.Queue):
    """Run Ollama chat in a child process so timeout can terminate it."""
    try:
        print("Before chat()", flush=True)
        response = chat(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_path],
                }
            ],
        )
        print("After chat()", flush=True)
        queue.put({"success": True, "response": response})
    except Exception:
        traceback.print_exc()
        queue.put({"success": False, "traceback": traceback.format_exc()})


class VisionManager:
    """Captures the screen and analyzes it with a local vision-capable model."""

    def __init__(self):
        self.model_name = self._select_model()

    def capture(self) -> Dict[str, Any]:
        """Capture a screenshot of the primary monitor."""
        start_time = time.perf_counter()
        output_path = Path(tempfile.gettempdir()) / "jarvis_screen.png"
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            "$bounds=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            "$bmp=New-Object System.Drawing.Bitmap $bounds.Width,$bounds.Height; "
            "$g=[System.Drawing.Graphics]::FromImage($bmp); "
            "$g.CopyFromScreen($bounds.Location,[System.Drawing.Point]::Empty,$bounds.Size); "
            f"$bmp.Save('{str(output_path)}',[System.Drawing.Imaging.ImageFormat]::Png); "
            "$g.Dispose(); $bmp.Dispose();"
        )

        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                check=True,
                capture_output=True,
                text=True,
            )
            elapsed = time.perf_counter() - start_time
            return {
                "success": True,
                "message": "Captured primary monitor screenshot",
                "path": str(output_path),
                "elapsed_capture_seconds": elapsed,
            }
        except Exception as exc:
            return {"success": False, "error": f"Screenshot capture failed: {exc}"}

    def analyze(self, image_path: str) -> Dict[str, Any]:
        """Analyze screenshot with the local model and return structured data."""
        print(f"Selected model: {self.model_name}", flush=True)
        resolved_image_path = str(Path(image_path).resolve())
        print(f"Image path: {resolved_image_path}", flush=True)

        file_exists = Path(image_path).is_file()
        file_size = Path(image_path).stat().st_size if file_exists else 0
        print(f"Screenshot exists: {file_exists}", flush=True)
        print(f"Screenshot size bytes: {file_size}", flush=True)

        if not file_exists:
            return {
                "success": False,
                "error": f"Screenshot not found: {resolved_image_path}",
            }

        prompt = (
            "Analyze this desktop screenshot and return strict JSON with keys: "
            "windows, buttons, text. "
            "Each key must map to a list. "
            "No markdown and no extra text."
        )

        try:
            queue: multiprocessing.Queue = multiprocessing.Queue()
            process = multiprocessing.Process(
                target=_chat_worker,
                args=(self.model_name, prompt, resolved_image_path, queue),
            )

            inference_start = time.perf_counter()
            process.start()
            process.join(timeout=600)

            if process.is_alive():
                process.terminate()
                process.join()
                return {
                    "success": False,
                    "error": "Vision model timeout after 600 seconds",
                }

            elapsed_inference = time.perf_counter() - inference_start
            if queue.empty():
                return {
                    "success": False,
                    "error": "Screen analysis failed: no response from vision process",
                }

            worker_result = queue.get()
            if not worker_result.get("success"):
                return {
                    "success": False,
                    "error": "Screen analysis failed in vision process",
                    "traceback": worker_result.get("traceback", ""),
                }

            response = worker_result.get("response")
            print(f"Raw Ollama response object: {response}", flush=True)

            content = response["message"]["content"].strip()
            parsed = self._parse_json(content)

            return {
                "success": True,
                "message": json.dumps(parsed, indent=2),
                "data": parsed,
                "elapsed_inference_seconds": elapsed_inference,
            }
        except Exception as exc:
            traceback.print_exc()
            return {"success": False, "error": f"Screen analysis failed: {exc}"}

    def _select_model(self) -> str:
        """Pick an installed vision-capable model when available."""
        try:
            response = ollama_list()
            models = [item.get("model", "") for item in response.get("models", [])]
        except Exception:
            return MODEL_NAME

        # Prefer explicit capability checks from model metadata.
        for model in models:
            if self._model_supports_vision(model):
                return model

        vision_keywords = [
            "llava",
            "bakllava",
            "moondream",
            "minicpm-v",
            "qwen2.5vl",
            "qwen2-vl",
            "gemma3",
            "gemma4",
        ]

        for model in models:
            lowered = model.lower()
            if any(keyword in lowered for keyword in vision_keywords):
                return model

        return MODEL_NAME

    def _model_supports_vision(self, model: str) -> bool:
        """Check model capabilities via ollama.show metadata."""
        try:
            metadata = ollama_show(model).model_dump()
        except Exception:
            return False

        capabilities = metadata.get("capabilities") or []
        return any(str(item).lower() == "vision" for item in capabilities)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse model output into a strict structured shape."""
        candidate = text
        if "```" in text:
            parts = [part.strip() for part in text.split("```") if part.strip()]
            if parts:
                candidate = parts[-1]
                if candidate.lower().startswith("json"):
                    candidate = candidate[4:].strip()

        data = json.loads(candidate)
        return {
            "windows": data.get("windows", []) if isinstance(data, dict) else [],
            "buttons": data.get("buttons", []) if isinstance(data, dict) else [],
            "text": data.get("text", []) if isinstance(data, dict) else [],
        }
