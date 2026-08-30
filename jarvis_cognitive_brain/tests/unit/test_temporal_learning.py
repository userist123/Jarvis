from jarvis.runtime.learning_dedup import LearningDeduplicator
from jarvis.runtime.temporal_learning import filter_learning_cases


def _case(observed_at: str):
    dedup = LearningDeduplicator()
    return dedup.record(
        goal="demo",
        lesson="lesson",
        risk="low",
        observation={
            "status": "success",
            "execution_id": "exec-1",
            "evidence_ids": ["e1"],
            "observed_at": observed_at,
        },
    )


def test_future_learning_case_is_excluded_from_historical_snapshot():
    case = _case("2026-08-20T12:00:00+00:00")
    included, snapshot = filter_learning_cases([case], as_of="2026-08-01")
    assert included == []
    assert case.case_id in snapshot.excluded_case_ids


def test_known_learning_case_is_included_in_historical_snapshot():
    case = _case("2026-07-20T12:00:00+00:00")
    included, snapshot = filter_learning_cases([case], known_as_of="2026-08-01")
    assert included == [case]
    assert case.case_id in snapshot.included_case_ids


def test_snapshot_can_use_both_time_axes():
    old = _case("2026-07-01T12:00:00+00:00")
    new = _case("2026-08-20T12:00:00+00:00")
    included, snapshot = filter_learning_cases(
        [old, new],
        as_of="2026-08-01",
        known_as_of="2026-08-15",
    )
    assert [c.case_id for c in included] == [old.case_id]
    assert new.case_id in snapshot.excluded_case_ids
