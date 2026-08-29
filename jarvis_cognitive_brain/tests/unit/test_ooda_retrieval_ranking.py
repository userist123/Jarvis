import pytest

from jarvis.config import Settings
from jarvis.core.cognitive_gateway import CognitiveGateway
from jarvis.core.models import PerceptionEvent
from jarvis.core.ooda import OODACognitiveEngine
from jarvis.llm.mock_provider import MockLLMProvider
from jarvis.memory.invariants import Lifecycle, NoteType
from jarvis.memory.sqlite_engine import SQLiteStorageEngine


@pytest.mark.asyncio
async def test_ooda_admits_ranked_memory_with_scores(tmp_path):
    storage = SQLiteStorageEngine(db_path=tmp_path / "memory.sqlite3", timeout=5)
    provider = MockLLMProvider()
    provider.set_next_response("ok")
    gateway = CognitiveGateway(settings=Settings(_env_file=None, sync_vault=False), provider=provider)

    def note(note_id, content, confidence):
        return {
            "id": note_id,
            "type": NoteType.KNOWLEDGE.value,
            "lifecycle": Lifecycle.ACTIVE.value,
            "category": "retrieval-test",
            "tags": [],
            "created": "2026-08-30",
            "updated": "2026-08-30",
            "provenance": {"source_type": "user", "source_ref": "test"},
            "confidence": confidence,
            "verification": "verified",
            "content": content,
            "relations": [],
        }

    storage.set_note_atomic(note("high", "SQLite memory retrieval system", "very_high"))
    storage.set_note_atomic(note("low", "SQLite database notes", "low"))

    engine = OODACognitiveEngine(llm_provider=provider, storage_engine=storage, cognitive_gateway=gateway, working_memory_capacity=1)
    result = await engine.execute_cycle(PerceptionEvent(channel="test", raw_data="SQLite memory retrieval system"))

    assert result.context_used
    assert result.context_used[0]["id"] == "high"
    assert "retrieval_score" in result.context_used[0]
    assert "retrieval_reason" in result.context_used[0]
