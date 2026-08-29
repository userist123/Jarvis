import uuid

import pytest

from jarvis.config import Settings
from jarvis.core.ooda import OODACognitiveEngine
from jarvis.memory.invariants import Lifecycle, NoteType
from jarvis.memory.sqlite_engine import SQLiteStorageEngine


@pytest.mark.asyncio
async def test_memory_store_duplicate_is_not_persisted_twice(tmp_path):
    storage = SQLiteStorageEngine(db_path=tmp_path / "memory.sqlite3", timeout=5)
    note_id = str(uuid.uuid4())
    storage.set_note_atomic({
        "id": note_id,
        "type": NoteType.KNOWLEDGE.value,
        "lifecycle": Lifecycle.ACTIVE.value,
        "category": "user-memory",
        "tags": ["memory-store"],
        "created": "2026-08-30",
        "updated": "2026-08-30",
        "provenance": {"source_type": "user", "source_ref": "test"},
        "confidence": "high",
        "verification": "verified",
        "applies_to": "JARVIS",
        "version_range": "local",
        "content": "Remember to use local Ollama for this project.",
        "relations": [],
    })

    engine = OODACognitiveEngine(llm_provider=None, storage_engine=storage)
    from jarvis.core.models import PerceptionEvent
    result = await engine.execute_cycle(
        PerceptionEvent(channel="test", raw_data="remember to use local Ollama for this project")
    )

    assert result.step_results
    step = result.step_results[0]
    assert step.status == "success"
    assert step.result["status"] in {"duplicate", "review"}
