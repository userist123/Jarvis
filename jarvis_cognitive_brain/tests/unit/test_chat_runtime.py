from __future__ import annotations

import json
from pathlib import Path

from jarvis.runtime.chat import ChatSession


def test_chat_session_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "chat_test.json"
    session = ChatSession(session_id="test")
    session.add("user", "hello")
    session.add("assistant", "hi")
    session.save(path)

    restored = ChatSession.load(path, "other")
    assert restored.session_id == "test"
    assert restored.messages == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_chat_session_ignores_malformed_entries(tmp_path: Path) -> None:
    path = tmp_path / "chat_test.json"
    path.write_text(
        json.dumps({"session_id": "x", "messages": ["bad", {"role": "user", "content": "ok"}]}),
        encoding="utf-8",
    )
    restored = ChatSession.load(path, "fallback")
    assert restored.messages == [{"role": "user", "content": "ok"}]
