from jarvis.runtime.learning_store import PersistentLearningStore
from jarvis.runtime.learning_dedup import LearningDeduplicator
from jarvis.runtime.learning_review_queue import LearningReviewQueue


def test_persistent_records_feed_review_queue(tmp_path):
    store = PersistentLearningStore(tmp_path / "learning.json")
    dedup = LearningDeduplicator()
    case = None
    for index in range(3):
        case = dedup.record(
            goal="restart service",
            lesson="retry after transient failure",
            risk="low",
            observation={
                "status": "success",
                "execution_id": f"exec-{index}",
                "evidence_ids": [f"ev-{index}"],
                "observed_at": f"2026-08-0{index + 1}T00:00:00+00:00",
            },
        )
    store.upsert(case)
    records = store.records()
    assert len(records) == 1
    assert records[0]["occurrences"] == 3
    assert LearningReviewQueue().build([case])[0].case_id == case.case_id
