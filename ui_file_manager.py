"""File and image handling utilities for multimodal input."""

from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image
import io


class FileManager:
    """Manages uploaded files, previews, and attachments."""

    SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    SUPPORTED_DOCS = {".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls", ".csv"}
    SUPPORTED_CODE = {".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rb", ".rs"}

    def __init__(self, max_file_size_mb=100):
        self.files: List[dict] = []
        self.max_file_size = max_file_size_mb * 1024 * 1024

    def add_file(self, file_path: str) -> Tuple[bool, str]:
        """Add a file and return (success, message)."""
        path = Path(file_path)
        if not path.exists():
            return False, "File not found"

        if path.stat().st_size > self.max_file_size:
            return False, f"File too large (max {self.max_file_size / 1024 / 1024:.0f}MB)"

        suffix = path.suffix.lower()
        file_type = self._get_file_type(suffix)
        if not file_type:
            return False, "File type not supported"

        self.files.append(
            {
                "path": str(path),
                "name": path.name,
                "type": file_type,
                "suffix": suffix,
                "size_bytes": path.stat().st_size,
            }
        )
        return True, f"Added {path.name}"

    def add_image_from_clipboard(self, image_data) -> Tuple[bool, str]:
        """Add image data from clipboard."""
        try:
            self.files.append(
                {
                    "path": None,
                    "name": "clipboard_image.png",
                    "type": "image",
                    "suffix": ".png",
                    "data": image_data,
                }
            )
            return True, "Added clipboard image"
        except Exception as e:
            return False, f"Failed to add clipboard image: {e}"

    def remove_file(self, index: int) -> Tuple[bool, str]:
        """Remove file by index."""
        if 0 <= index < len(self.files):
            removed = self.files.pop(index)
            return True, f"Removed {removed['name']}"
        return False, "File not found"

    def clear_files(self) -> None:
        """Clear all files."""
        self.files = []

    def get_image_preview(self, index: int, size: Tuple[int, int] = (200, 200)) -> Optional[bytes]:
        """Get a PNG preview of an image file."""
        if not (0 <= index < len(self.files)):
            return None

        file_info = self.files[index]
        if file_info["type"] != "image":
            return None

        try:
            if "data" in file_info:
                img = Image.open(io.BytesIO(file_info["data"]))
            else:
                img = Image.open(file_info["path"])

            img.thumbnail(size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception:
            return None

    def get_file_icon(self, suffix: str) -> str:
        """Get a text icon for a file type."""
        icon_map = {
            ".pdf": "📄",
            ".txt": "📝",
            ".py": "🐍",
            ".js": "⚙️",
            ".json": "{ }",
            ".csv": "📊",
            ".xlsx": "📊",
            ".doc": "📘",
            ".docx": "📘",
            ".png": "🖼️",
            ".jpg": "🖼️",
            ".gif": "🎞️",
        }
        return icon_map.get(suffix.lower(), "📎")

    def _get_file_type(self, suffix: str) -> Optional[str]:
        """Determine file type from suffix."""
        suffix = suffix.lower()
        if suffix in self.SUPPORTED_IMAGES:
            return "image"
        if suffix in self.SUPPORTED_DOCS:
            return "document"
        if suffix in self.SUPPORTED_CODE:
            return "code"
        if suffix == ".folder":
            return "folder"
        return None

    def list_files(self) -> List[dict]:
        """List all added files."""
        return self.files.copy()
