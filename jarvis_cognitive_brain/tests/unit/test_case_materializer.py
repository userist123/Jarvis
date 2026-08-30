from __future__ import annotations

from pathlib import Path

from jarvis.runtime.case_materializer import CaseMaterializer
from jarvis.runtime.memory_case_store import MemoryCaseStore


def _signal(signal_type: str, signal_id: str = "sig-1") -> dict:
    return {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "memory_ids": ["m1", "m2"],
        "severity": "high",
        "confidence": 0.8,
        "reason": "test signal",
        "metadata": {},
    }


def test_non_conflict_materializes_provisional(tmp_path: Path) -> None:
    store = MemoryCaseStore(tmp_path / "cases.jsonl")
    result = CaseMaterializer(store).materialize(_signal("DUPLICATE"))
    assert result.canonical is False
    assert result.route == "LEARNING_REVIEW"
    assert result.case_id == "MC-sig-1"


def test_conflict_materializes_canonical_and_is_idempotent(tmp_path: Path) -> None:
    store = MemoryCaseStore(tmp_path / "cases.jsonl")
    calls: list[dict] = []

    class ConflictStub:
        def open_case(self, **kwargs):
            calls.append(kwargs)
            return {"case_id": "CR-100"}

    materializer = CaseMaterializer(store, ConflictStub())
    first = materializer.materialize(_signal("POTENTIAL_CONTRADICTION"))
    second = materializer.materialize(_signal("POTENTIAL_CONTRADICTION"))

    assert first.canonical is True
    assert first.case_id == "CR-100"
    assert second.case_id == "CR-100"
    assert len(calls) == 1
    persisted = store.get_by_signal("sig-1")
    assert persisted is not None
    assert persisted["canonical_case_id"] == "CR-100"
