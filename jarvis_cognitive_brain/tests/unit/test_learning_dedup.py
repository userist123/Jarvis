from jarvis.runtime.learning_dedup import LearningDeduplicator, fingerprint_learning


def test_identical_learning_events_share_case_and_accumulate_evidence():
    dedup = LearningDeduplicator()
    obs1 = {"execution_id": "e1", "status": "error", "evidence_ids": ["ev1"]}
    obs2 = {"execution_id": "e2", "status": "error", "evidence_ids": ["ev2"]}
    first = dedup.record(goal="deploy", lesson="restart service", risk="medium", observation=obs1)
    second = dedup.record(goal="deploy", lesson="restart service", risk="medium", observation=obs2)
    assert first.case_id == second.case_id
    assert second.occurrences == 2
    assert second.execution_ids == {"e1", "e2"}
    assert second.evidence_ids == {"ev1", "ev2"}


def test_high_risk_event_upgrades_existing_case():
    dedup = LearningDeduplicator()
    obs = {"execution_id": "e3", "status": "blocked", "evidence_ids": []}
    case = dedup.record(goal="x", lesson="y", risk="low", observation=obs)
    assert case.risk == "high"


def test_fingerprint_is_deterministic():
    assert fingerprint_learning(" Deploy ", " Restart Service ") == fingerprint_learning("deploy", "restart service")
