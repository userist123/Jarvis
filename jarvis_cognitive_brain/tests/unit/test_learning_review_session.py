import json

from jarvis.runtime.learning_review_session import LearningReviewSessionService
from jarvis.runtime.learning_store import PersistentLearningStore


def test_review_session_is_read_only_and_temporal(tmp_path):
    path = tmp_path / "learning_cases.json"
    record = {
        "case_id": "LC-1234567890abcdef",
        "fingerprint": "f" * 64,
        "goal": "deploy service",
        "lesson": "use rollback",
        "risk": "low",
        "observations": [
            {"observed_at": "2026-08-01T10:00:00+00:00", "knowledge_time": "2026-08-01T10:00:00+00:00", "status": "success", "evidence_ids": ["e1"], "execution_id": "x1"},
            {"observed_at": "2026-08-20T10:00:00+00:00", "knowledge_time": "2026-08-20T10:00:00+00:00", "status": "success", "evidence_ids": ["e2"], "execution_id": "x2"},
        ],
    }
    path.write_text(json.dumps([record]), encoding="utf-8")
    session = LearningReviewSessionService(PersistentLearningStore(path)).open(
        "LC-1234567890abcdef", as_of="2026-08-10", known_as_of="2026-08-10"
    )
    payload = session.as_dict()
    assert payload["read_only"] is True
    assert payload["case"]["occurrences"] == 1
    assert payload["case"]["evidence_ids"] == ["e1"]
    assert payload["confidence_snapshot"]["as_of"] == "2026-08-10T00:00:00"
    assert payload["temporal"]["visible_observations"] == 1
    assert "OPEN_REVIEW" in payload["proposed_actions"]
