import uuid
from pathlib import Path

import pytest

from jarvis.core.ooda import OODACognitiveEngine
from jarvis.core.cognitive_gateway import CognitiveGateway
from jarvis.core.models import PerceptionEvent
from jarvis.llm.mock_provider import MockLLMProvider
from jarvis.memory.invariants import Lifecycle, NoteType
from jarvis.memory.sqlite_engine import SQLiteStorageEngine


@pytest.mark.asyncio
async def test_ooda_synthesis_uses_cognitive_gateway(monkeypatch, tmp_path: Path):
    storage = SQLiteStorageEngine(db_path=tmp_path / "memory.sqlite3", timeout=5)
    provider = MockLLMProvider()
    provider.set_next_response("Memory-grounded answer")

    vault = tmp_path / "AI_Memory_Vault_CODEX_READY"
    vault.mkdir()
    (vault / "AGENTS.md").write_text("Canonical memory rules", encoding="utf-8")

    from jarvis.config import Settings
    settings = Settings(vault_path=vault, sync_vault=False)
    gateway = CognitiveGateway(settings=settings, provider=provider)

    note_id = str(uuid.uuid4())
    storage.set_note_atomic({
        "id": note_id,
        "type": NoteType.KNOWLEDGE.value,
        "lifecycle": Lifecycle.ACTIVE.value,
        "category": "test",
        "tags": ["ooda"],
        "created": "2026-08-30",
        "updated": "2026-08-30",
        "provenance": {"source_type": "user", "source_ref": "test"},
        "confidence": "high",
        "verification": "verified",
        "content": "Canonical memory answer context.",
        "relations": [],
    })

    engine = OODACognitiveEngine(
        llm_provider=provider,
        storage_engine=storage,
        cognitive_gateway=gateway,
    )
    result = await engine.execute_cycle(
        PerceptionEvent(channel="test", raw_data="What is the canonical memory context?")
    )

    assert result.step_results[0].status == "success"
    assert result.step_results[0].result["answer"] == "Memory-grounded answer"
