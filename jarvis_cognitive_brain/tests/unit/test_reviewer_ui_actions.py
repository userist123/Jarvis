from jarvis.runtime.reviewer_actions import derive_reviewer_actions


def test_ai_agent_cannot_decide_or_mutate():
    actions = derive_reviewer_actions(
        review_state={"state": "DECISION_PENDING", "can_apply_mutation": False},
        evidence_verification={"valid": True, "bundle_hash_matches": True},
        principal="AI_AGENT",
        confidence={"promotable": True},
    )
    assert actions.inspect is True
    assert actions.approve is False
    assert actions.reject is False
    assert actions.defer is False
    assert actions.mutate is False


def test_human_approved_valid_evidence_can_mutate():
    actions = derive_reviewer_actions(
        review_state={"state": "APPROVED", "can_apply_mutation": True},
        evidence_verification={"valid": True, "bundle_hash_matches": True},
        principal="HUMAN",
        confidence={"promotable": True},
    )
    assert actions.mutate is True
    assert actions.approve is False


def test_invalid_evidence_disables_mutation():
    actions = derive_reviewer_actions(
        review_state={"state": "APPROVED", "can_apply_mutation": True},
        evidence_verification={"valid": False, "bundle_hash_matches": False},
        principal="HUMAN",
    )
    assert actions.mutate is False
