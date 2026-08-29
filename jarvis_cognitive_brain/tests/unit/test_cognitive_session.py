from pathlib import Path

from jarvis.core.cognitive_session import CognitiveSession


def test_checkpoint_and_restore(tmp_path: Path):
    path = tmp_path / "session.json"
    session = CognitiveSession(session_id="s1", goal="test", plan_id="p1", tick=4)
    session.record_activation("note-1", 0.75)
    session.checkpoint(path)

    restored = CognitiveSession.restore(path)
    assert restored.session_id == "s1"
    assert restored.goal == "test"
    assert restored.plan_id == "p1"
    assert restored.tick == 4
    assert restored.active_nodes == [{"id": "note-1", "activation": 0.75}]


def test_checkpoint_does_not_store_canonical_content(tmp_path: Path):
    path = tmp_path / "session.json"
    session = CognitiveSession(goal="test")
    session.record_activation("note-1", 0.5)
    session.checkpoint(path)
    raw = path.read_text(encoding="utf-8")
    assert "content" not in raw
