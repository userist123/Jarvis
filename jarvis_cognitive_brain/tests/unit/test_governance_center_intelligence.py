from pathlib import Path

from jarvis.runtime.governance_center import GovernanceCenterService
from jarvis.runtime.learning_store import PersistentLearningStore
from jarvis.runtime.memory_intelligence import MemorySignal
from jarvis.runtime.memory_intelligence_store import MemoryIntelligenceStore
from jarvis.runtime.review_state_store import PersistentReviewStateStore


def test_governance_center_includes_intelligence_summary(tmp_path: Path):
    learning = PersistentLearningStore(tmp_path / "learning.json")
    review_states = PersistentReviewStateStore(tmp_path / "review.jsonl")
    intelligence_store = MemoryIntelligenceStore(tmp_path / "intelligence.jsonl")
    intelligence_store.upsert(
        MemorySignal(
            signal_id="sig-1",
            signal_type="POTENTIAL_CONTRADICTION",
            memory_ids=("A", "B"),
            severity="high",
            confidence=0.65,
            reason="test",
            metadata={},
            detected_at="2026-08-30T00:00:00+00:00",
        )
    )
    service = GovernanceCenterService(learning, review_states, intelligence_store)
    result = service.build(identity={"subject": "tester", "principal": "HUMAN", "authenticated": True})
    payload = result.as_dict()
    assert payload["intelligence"]["total"] == 1
    assert payload["intelligence"]["by_route"]["CONFLICT_REVIEW"] == 1
    assert payload["read_only"] is True
