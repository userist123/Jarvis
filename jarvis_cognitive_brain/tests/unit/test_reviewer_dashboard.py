from jarvis.runtime.learning_store import PersistentLearningStore
from jarvis.runtime.reviewer_dashboard import ReviewerDashboardService
from jarvis.runtime.review_state_store import PersistentReviewStateStore
from jarvis.runtime.learning_dedup import LearningCase


def _case(case_id: str, risk: str, status: str) -> LearningCase:
    case = LearningCase(
        case_id=case_id,
        fingerprint=case_id,
        goal="test goal",
        lesson="test lesson",
        risk=risk,
    )
    case.add({
        "observed_at": "2026-08-01T00:00:00+00:00",
        "knowledge_time": "2026-08-01T00:00:00+00:00",
        "status": status,
        "evidence_ids": [f"ev-{case_id}"],
        "execution_id": f"exec-{case_id}",
    })
    return case


def test_dashboard_is_read_only_and_aggregates(tmp_path):
    learning_store = PersistentLearningStore(tmp_path / "learning.json")
    case = _case("LC-1", "high", "success")
    learning_store.upsert(case)
    state_store = PersistentReviewStateStore(tmp_path / "states.jsonl")
    state_store.ensure_open("CR-1")

    dashboard = ReviewerDashboardService(learning_store, state_store).build(top_n=5).as_dict()

    assert dashboard["read_only"] is True
    assert dashboard["total_cases"] == 1
    assert dashboard["high_risk"] == 1
    assert dashboard["by_risk"]["high"] == 1
    assert dashboard["top_priority"][0]["case_id"] == "LC-1"
