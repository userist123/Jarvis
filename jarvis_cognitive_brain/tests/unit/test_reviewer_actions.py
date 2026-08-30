from jarvis.runtime.reviewer_actions import derive_reviewer_actions


def test_decision_pending_allows_human_decision():
    actions = derive_reviewer_actions(
        review_state={"state": "DECISION_PENDING", "can_apply_mutation": False},
        principal="HUMAN",
    )
    assert actions.inspect is True
    assert actions.approve is True
    assert actions.reject is True
    assert actions.defer is True
    assert actions.mutate is False


def test_approved_without_verified_evidence_cannot_mutate():
    actions = derive_reviewer_actions(
        review_state={"state": "APPROVED", "can_apply_mutation": True},
        evidence_verification={"valid": False, "bundle_hash_matches": False},
        principal="ADMIN",
    )
    assert actions.close is True
    assert actions.mutate is False


def test_ai_agent_cannot_decide_or_mutate():
    actions = derive_reviewer_actions(
        review_state={"state": "DECISION_PENDING", "can_apply_mutation": False},
        evidence_verification={"valid": True, "bundle_hash_matches": True},
        principal="AI_AGENT",
    )
    assert actions.approve is False
    assert actions.reject is False
    assert actions.defer is False
    assert actions.mutate is False
