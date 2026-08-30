from jarvis.runtime.learning_eligibility import assess_learning_eligibility


def test_success_is_learning_eligible_low_risk():
    result = assess_learning_eligibility({"status": "success", "evidence_ids": ("e1",)})
    assert result.eligible is True
    assert result.risk == "low"


def test_error_is_learning_eligible_medium_risk():
    result = assess_learning_eligibility({"status": "error"})
    assert result.eligible is True
    assert result.risk == "medium"


def test_unknown_status_is_not_learning_eligible():
    result = assess_learning_eligibility({"status": "not_executed"})
    assert result.eligible is False


def test_risky_capability_is_high_risk():
    result = assess_learning_eligibility({"status": "success", "risky_capability": True})
    assert result.eligible is True
    assert result.risk == "high"
