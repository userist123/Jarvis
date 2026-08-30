from jarvis.core.self_improvement import SelfImprovementWorkflow


def test_candidate_without_evidence_is_not_promotion_ready():
    candidate = SelfImprovementWorkflow().create_candidate(
        lesson="Do not reuse a failed command",
        success=False,
        evidence_ids=(),
    )
    assert candidate.lifecycle == "REVIEW"
    assert candidate.verification == "unverified"
    assert candidate.promotion_ready is False
    assert candidate.risk == "high"


def test_successful_candidate_with_evidence_is_low_risk_but_still_review():
    candidate = SelfImprovementWorkflow().create_candidate(
        lesson="Use the local cache before a remote lookup",
        success=True,
        evidence_ids=("obs-1", "obs-2"),
    )
    assert candidate.lifecycle == "REVIEW"
    assert candidate.verification == "unverified"
    assert candidate.promotion_ready is False
    assert candidate.risk == "low"


def test_verified_candidate_is_promotion_ready_without_becoming_active():
    workflow = SelfImprovementWorkflow()
    candidate = workflow.create_candidate(
        lesson="Prefer deterministic parsing",
        success=True,
        evidence_ids=("obs-1",),
    )
    verified = workflow.mark_verified(candidate, evidence_valid=True)
    assert verified.verification == "verified"
    assert verified.promotion_ready is True
    assert verified.lifecycle == "REVIEW"


def test_invalid_evidence_does_not_verify_candidate():
    workflow = SelfImprovementWorkflow()
    candidate = workflow.create_candidate(
        lesson="Keep failed attempts out of active memory",
        success=False,
        evidence_ids=("obs-1",),
    )
    result = workflow.mark_verified(candidate, evidence_valid=False)
    assert result == candidate
