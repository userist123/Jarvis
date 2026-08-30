from jarvis.runtime.learning_confidence import assess_learning_confidence
from jarvis.runtime.learning_dedup import LearningCase


def _case(*, occurrences=3, evidence=3, successes=3, errors=0, risk="low"):
    case = LearningCase(
        case_id="LC-test",
        fingerprint="fp",
        goal="demo",
        lesson="same lesson",
        risk=risk,
    )
    case.occurrences = occurrences
    case.evidence_ids = {f"ev-{i}" for i in range(evidence)}
    case.outcome_counts = {"success": successes, "error": errors}
    case.statuses = {k for k, v in case.outcome_counts.items() if v}
    return case


def test_repeated_success_with_multiple_evidence_is_promotable():
    confidence = assess_learning_confidence(_case())
    assert confidence.promotable is True
    assert confidence.score >= 0.75


def test_repeated_success_with_failures_is_not_promotable():
    confidence = assess_learning_confidence(_case(occurrences=4, evidence=3, successes=2, errors=2))
    assert confidence.promotable is False
    assert "promotion criteria not satisfied" in confidence.reasons


def test_high_risk_case_is_never_promotable():
    confidence = assess_learning_confidence(_case(risk="high"))
    assert confidence.promotable is False
    assert confidence.risk_penalty > 0
