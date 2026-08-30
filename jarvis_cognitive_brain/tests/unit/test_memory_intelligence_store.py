from pathlib import Path

from jarvis.runtime.memory_intelligence import MemorySignal
from jarvis.runtime.memory_intelligence_store import MemoryIntelligenceStore


def test_signal_store_round_trip_and_dedup(tmp_path: Path):
    store = MemoryIntelligenceStore(tmp_path / "signals.jsonl")
    signal = MemorySignal(
        signal_id="sig-1",
        signal_type="DUPLICATE",
        memory_ids=("A", "B"),
        severity="medium",
        confidence=1.0,
        reason="duplicate",
        metadata={"count": 2},
        detected_at="2026-08-30T00:00:00+00:00",
    )

    assert store.upsert_many([signal, signal]) == 1
    assert store.get("sig-1")["memory_ids"] == ["A", "B"]

    restored = MemoryIntelligenceStore(tmp_path / "signals.jsonl")
    assert restored.records() == store.records()
