from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from jarvis.config import Settings, get_settings
from jarvis.core.cognitive_gateway import CognitiveGateway
from jarvis.llm.base import CancellationToken


@dataclass
class ChatSession:
    """Small local conversation checkpoint; canonical memory stays in the Vault."""

    session_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(
                {"session_id": self.session_id, "messages": self.messages},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path, session_id: str) -> "ChatSession":
        if not path.exists():
            return cls(session_id=session_id)
        try:
            data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            messages = data.get("messages", [])
            if not isinstance(messages, list):
                messages = []
            normalized = [
                {"role": str(item.get("role", "user")), "content": str(item.get("content", ""))}
                for item in messages
                if isinstance(item, dict) and item.get("content")
            ]
            return cls(session_id=str(data.get("session_id") or session_id), messages=normalized)
        except (OSError, ValueError, TypeError):
            return cls(session_id=session_id)


class ChatRuntime:
    """Interactive local-first chat runtime using the shared CognitiveGateway."""

    def __init__(self, settings: Settings | None = None, session_id: str = "default") -> None:
        self.settings = settings or get_settings()
        self.gateway = CognitiveGateway(settings=self.settings)
        self.session_id = session_id
        self.path = self.settings.session_memory_path.with_name(
            f"chat_{session_id}.json"
        )
        self.session = ChatSession.load(self.path, session_id)

    async def stream_reply(self, user_text: str) -> str:
        self.session.add("user", user_text)
        system_prompt = (
            "You are JARVIS running locally. "
            "Use the canonical AI Memory Vault context supplied by the gateway. "
            "Do not claim actions were executed unless an execution result exists. "
            "When evidence is unavailable or conflicting, say so explicitly."
        )
        token = CancellationToken()
        chunks: List[str] = []
        print("JARVIS: ", end="", flush=True)
        async for chunk in self.gateway.provider("reasoning").stream(
            self.gateway.build_system_prompt(system_prompt),
            cancellation_token=token,
        ):
            chunks.append(chunk)
            print(chunk, end="", flush=True)
        print()
        answer = "".join(chunks)
        self.session.add("assistant", answer)
        self.session.save(self.path)
        return answer

    async def reply(self, user_text: str) -> str:
        self.session.add("user", user_text)
        system_prompt = (
            "You are JARVIS running locally. "
            "Use the canonical AI Memory Vault context supplied by the gateway. "
            "Do not claim actions were executed unless an execution result exists. "
            "When evidence is unavailable or conflicting, say so explicitly."
        )
        answer = await self.gateway.chat(
            self.session.messages,
            capability="reasoning",
            system_prompt=system_prompt,
        )
        self.session.add("assistant", answer)
        self.session.save(self.path)
        return answer

    def reset(self) -> None:
        self.session = ChatSession(session_id=self.session_id)
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
