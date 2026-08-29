"""Session lifecycle management for restart-safe JARVIS cognition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from jarvis.config import Settings, get_settings
from jarvis.core.cognitive_session import CognitiveSession


@dataclass(frozen=True)
class SessionResumeResult:
    session: CognitiveSession
    resumed: bool
    checkpoint_path: Path


class SessionManager:
    """Manage lightweight checkpoints without duplicating canonical memory."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.root = Path(self.settings.checkpoint_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, session_id: str) -> Path:
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        if not safe_id:
            raise ValueError("Invalid session id")
        return self.root / f"{safe_id}.json"

    def create(self, goal: str = "") -> CognitiveSession:
        session = CognitiveSession(goal=goal)
        session.checkpoint(self.path_for(session.session_id))
        return session

    def save(self, session: CognitiveSession) -> Path:
        return session.checkpoint(self.path_for(session.session_id))

    def resume(self, session_id: str) -> SessionResumeResult:
        path = self.path_for(session_id)
        if not path.is_file():
            return SessionResumeResult(
                session=CognitiveSession(session_id=session_id),
                resumed=False,
                checkpoint_path=path,
            )
        return SessionResumeResult(
            session=CognitiveSession.restore(path),
            resumed=True,
            checkpoint_path=path,
        )

    def list_sessions(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.json") if p.is_file())
