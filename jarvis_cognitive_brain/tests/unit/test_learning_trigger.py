from jarvis.runtime.learning_trigger import LearningTrigger


def test_not_executed_does_not_trigger_learning():
    trigger = LearningTrigger()
    case = trigger.observe(
        goal="x",
        lesson="y",
        observation={"execution_id": "e1", "status": "not_executed"},
    )
    assert case is None
    assert trigger.deduplicator.all() == []


def test_blocked_execution_triggers_high_risk_case():
    trigger = LearningTrigger()
    case = trigger.observe(
        goal="x",
        lesson="needs review",
        observation={"execution_id": "e2", "status": "blocked"},
    )
    assert case is not None
    assert case.risk == "high"
    assert case.occurrences == 1
