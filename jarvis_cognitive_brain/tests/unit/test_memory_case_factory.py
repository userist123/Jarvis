from jarvis.runtime.memory_case_factory import MemoryCaseFactory
from jarvis.runtime.memory_case_store import MemoryCaseStore


def signal(kind: str = "POTENTIAL_CONTRADICTION") -> dict:
    return {
        "signal_id": "sig-001",
        "signal_type": kind,
        "memory_ids": ["m1", "m2"],
        "severity": "high",
        "confidence": 0.8,
        "reason": "test",
        "metadata": {"x": 1},
    }


def test_factory_is_idempotent() -> None:
    factory = MemoryCaseFactory()
    first = factory.create_from_signal(signal())
    second = factory.create_from_signal(signal())
    assert first == second
    assert first["case_id"] == "MC-sig-001"
    assert first["kind"] == "conflict"
    assert first["route"] == "CONFLICT_REVIEW"


def test_routes_all_known_signal_types() -> None:
    expected = {
        "POTENTIAL_CONTRADICTION": ("conflict", "CONFLICT_REVIEW"),
        "DUPLICATE": ("learning", "LEARNING_REVIEW"),
        "STALE": ("memory", "MEMORY_REVIEW"),
        "KNOWLEDGE_GAP": ("acquisition", "KNOWLEDGE_ACQUISITION"),
    }
    for kind, pair in expected.items():
        item = MemoryCaseFactory().create_from_signal(signal(kind) | {"signal_id": f"{kind}-1"})
        assert (item["kind"], item["route"]) == pair


def test_store_persists_signal_mapping(tmp_path) -> None:
    path = tmp_path / "cases.jsonl"
    store = MemoryCaseStore(path)
    first = store.create_from_signal(signal())
    second = MemoryCaseStore(path).create_from_signal(signal())
    assert first["case_id"] == second["case_id"]
    assert len(MemoryCaseStore(path).records()) == 1
