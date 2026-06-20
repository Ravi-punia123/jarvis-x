"""History manager for chat sessions and conversations."""

from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json


class HistoryManager:
    """Manages chat history, session persistence, and searching."""

    def __init__(self, history_file: str = "chat_history.json"):
        self.history_file = Path(history_file)
        self.current_session: List[dict] = []
        self.sessions: List[dict] = []
        self._load_sessions()

    def new_session(self, title: str = "New Chat") -> None:
        """Start a new chat session."""
        if self.current_session:
            self.save_session(title)
        self.current_session = []

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add a message to current session."""
        self.current_session.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
        )

    def save_session(self, title: str = "Chat") -> None:
        """Save current session to history."""
        if not self.current_session:
            return

        next_id = max([s.get("id", -1) for s in self.sessions], default=-1) + 1
        session = {
            "id": next_id,
            "title": title,
            "created": datetime.now().isoformat(),
            "messages": self.current_session.copy(),
            "pinned": False,
        }
        self.sessions.append(session)
        self._persist()

    def get_sessions(self) -> List[dict]:
        """Get all saved sessions."""
        return self.sessions.copy()

    def get_session(self, session_id: int) -> Optional[List[dict]]:
        """Get messages from a specific session."""
        for session in self.sessions:
            if session["id"] == session_id:
                return session["messages"].copy()
        return None

    def delete_session(self, session_id: int) -> bool:
        """Delete a session by ID."""
        for i, session in enumerate(self.sessions):
            if session["id"] == session_id:
                self.sessions.pop(i)
                self._persist()
                return True
        return False

    def rename_session(self, session_id: int, new_title: str) -> bool:
        """Rename a session."""
        for session in self.sessions:
            if session["id"] == session_id:
                session["title"] = new_title.strip()
                self._persist()
                return True
        return False

    def pin_session(self, session_id: int) -> bool:
        """Pin/unpin a session."""
        for session in self.sessions:
            if session["id"] == session_id:
                session["pinned"] = not session.get("pinned", False)
                self._persist()
                return True
        return False

    def search_sessions(self, query: str) -> List[dict]:
        """Search sessions by title or message content."""
        query_lower = query.lower()
        results = []
        for session in self.sessions:
            if query_lower in session["title"].lower():
                results.append(session)
            else:
                for msg in session.get("messages", []):
                    if query_lower in msg.get("content", "").lower():
                        results.append(session)
                        break
        return results

    def get_pinned_sessions(self) -> List[dict]:
        """Get all pinned sessions."""
        return [s for s in self.sessions if s.get("pinned", False)]

    def _load_sessions(self) -> None:
        """Load sessions from disk."""
        if not self.history_file.exists():
            return
        try:
            data = json.loads(self.history_file.read_text())
            self.sessions = data.get("sessions", [])
        except Exception:
            self.sessions = []

    def _persist(self) -> None:
        """Save sessions to disk."""
        self.history_file.write_text(
            json.dumps({"sessions": self.sessions}, indent=2),
            encoding="utf-8",
        )

    def export_session(self, session_id: int, format: str = "json") -> Optional[str]:
        """Export session as JSON or markdown."""
        session = None
        for s in self.sessions:
            if s["id"] == session_id:
                session = s
                break
        if not session:
            return None

        if format == "markdown":
            lines = [f"# {session['title']}\n"]
            for msg in session.get("messages", []):
                role = msg["role"].upper()
                content = msg["content"]
                lines.append(f"**{role}**: {content}\n")
            return "\n".join(lines)
        else:
            return json.dumps(session, indent=2)

    def import_session(self, source_path: str) -> bool:
        """Import a conversation from JSON export."""
        try:
            payload = json.loads(Path(source_path).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return False
            if "messages" not in payload or not isinstance(payload["messages"], list):
                return False

            next_id = max([s.get("id", -1) for s in self.sessions], default=-1) + 1
            imported = {
                "id": next_id,
                "title": str(payload.get("title", "Imported Chat")),
                "created": datetime.now().isoformat(),
                "messages": payload["messages"],
                "pinned": False,
            }
            self.sessions.append(imported)
            self._persist()
            return True
        except Exception:
            return False
