from pathlib import Path

from jarvis.runtime.memory_intelligence import MemorySignal
from jarvis.runtime.memory_intelligence_store import MemoryIntelligenceStore
from jarvis.runtime.memory_intelligence_triage_service import MemoryIntelligenceTriageService


def test_service_uses_persisted_signals(tmp_path: Path):
    store = MemoryIntelligenceStore(tmp_path / "signals.jsonl")
    store.upsert_many([
        MemorySignal(
            signal_id="s1",
            signal_type="POTENTIAL_CONTRADICTION",
            memory_ids=("A", "B"),
            severity="high",
            confidence=0.65,
            reason="test",
            metadata={},
            detected_at="2026-08-30T00:00:00+00:00",
        ),
        MemorySignal(
            signal_id="s2",
            signal_type="KNOWLEDGE_GAP",
            memory_ids=(),
            severity="low",
            confidence=0.90,
            reason="test",
            metadata={},
            detected_at="2026-08-30T00:00:00+00:00",
        ),
    ])
    service = MemoryIntelligenceTriageService(store)
    summary = service.summary()
    assert summary["total"] == 2
    assert summary["by_route"]["CONFLICT_REVIEW"] == 1
    assert summary["by_route"]["KNOWLEDGE_ACQUISITION"] == 1
    assert summary["read_only"] is True
