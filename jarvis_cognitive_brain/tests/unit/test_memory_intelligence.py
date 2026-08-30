from datetime import datetime, timezone, timedelta

from jarvis.runtime.memory_intelligence import (
    MemorySignalType,
    detect_knowledge_gap,
    detect_potential_contradictions,
    detect_stale,
    detect_duplicates,
    scan,
)


def test_exact_duplicate_is_detected():
    records = [{"id": "A", "content": "Same claim."}, {"id": "B", "content": "Same claim."}]
    signals = detect_duplicates(records)
    assert len(signals) == 1
    assert signals[0].signal_type == MemorySignalType.DUPLICATE
    assert set(signals[0].memory_ids) == {"A", "B"}


def test_potential_contradiction_requires_different_variants():
    records = [
        {"id": "A", "content": "Server port is 8080."},
        {"id": "B", "content": "Server port is 9090."},
    ]
    signals = detect_potential_contradictions(records)
    assert len(signals) == 1
    assert signals[0].signal_type == MemorySignalType.POTENTIAL_CONTRADICTION
    assert signals[0].confidence < 1.0


def test_stale_uses_updated_timestamp():
    now = datetime(2026, 8, 30, tzinfo=timezone.utc)
    old = (now - timedelta(days=200)).isoformat()
    signals = detect_stale([{"id": "A", "content": "old", "updated_at": old}], max_age_days=180, now=now)
    assert len(signals) == 1
    assert signals[0].signal_type == MemorySignalType.STALE


def test_knowledge_gap_requires_empty_results():
    assert len(detect_knowledge_gap("unknown topic", [])) == 1
    assert detect_knowledge_gap("known topic", [{"id": "A"}]) == []


def test_scan_combines_and_sorts_signals():
    records = [
        {"id": "A", "content": "Same claim."},
        {"id": "B", "content": "Same claim."},
        {"id": "C", "content": "Server port is 8080."},
        {"id": "D", "content": "Server port is 9090."},
    ]
    signals = scan(records)
    assert {signal.signal_type for signal in signals} == {
        MemorySignalType.DUPLICATE,
        MemorySignalType.POTENTIAL_CONTRADICTION,
    }
    assert signals == sorted(signals, key=lambda item: (-item.confidence, item.signal_type, item.signal_id))
