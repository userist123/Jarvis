from jarvis.runtime.learning_dedup import LearningDeduplicator
from jarvis.runtime.learning_review_queue import LearningReviewQueue


def _case(*, risk="low", count=1):
    d = LearningDeduplicator()
    case = None
    for index in range(count):
        case = d.record(
            goal="same goal",
            lesson="same lesson",
            risk=risk,
            observation={
                "status": "success",
                "execution_id": f"exec-{index}",
                "evidence_ids": [f"ev-{index}"],
                "observed_at": f"2026-08-0{index + 1}T00:00:00+00:00",
            },
        )
    return case


def test_queue_prioritizes_high_risk():
    high = _case(risk="high", count=1)
    low = _case(risk="low", count=3)
    items = LearningReviewQueue().build([low, high])
    assert items[0].case_id == high.case_id


def test_queue_is_deterministic():
    case = _case(risk="medium", count=2)
    first = LearningReviewQueue().build([case])[0].as_dict()
    second = LearningReviewQueue().build([case])[0].as_dict()
    assert first == second
