from jarvis.runtime.learning_dedup import LearningCase
from jarvis.runtime.temporal_confidence import assess_temporal_learning_confidence


def _case():
    case = LearningCase("LC-test", "fp", "deploy", "deploy lesson", "low")
    case.add({"observed_at": "2026-08-01T10:00:00+00:00", "knowledge_time": "2026-08-01T10:00:00+00:00", "status": "success", "evidence_ids": ["e1"], "execution_id": "x1"})
    case.add({"observed_at": "2026-08-02T10:00:00+00:00", "knowledge_time": "2026-08-02T10:00:00+00:00", "status": "success", "evidence_ids": ["e2"], "execution_id": "x2"})
    case.add({"observed_at": "2026-08-20T10:00:00+00:00", "knowledge_time": "2026-08-20T10:00:00+00:00", "status": "success", "evidence_ids": ["e3"], "execution_id": "x3"})
    return case


def test_temporal_confidence_excludes_future_observation():
    case = _case()
    current, _ = assess_temporal_learning_confidence([case])
    snapshot, meta = assess_temporal_learning_confidence([case], as_of="2026-08-10", known_as_of="2026-08-10")
    assert current[0][0].occurrences == 3
    assert snapshot[0][0].occurrences == 2
    assert snapshot[0][1].evidence_score < current[0][1].evidence_score
    assert meta.as_of == "2026-08-10T00:00:00"


def test_temporal_confidence_excludes_case_not_yet_known():
    case = _case()
    result, meta = assess_temporal_learning_confidence([case], known_as_of="2026-07-01")
    assert result == []
    assert meta.excluded_case_ids == ("LC-test",)
