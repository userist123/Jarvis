from jarvis.runtime.review_automation import ReviewAutomation
from jarvis.runtime.review_state_store import PersistentReviewStateStore


def test_valid_verification_advances_to_decision_pending(tmp_path):
    store = PersistentReviewStateStore(tmp_path / "states.jsonl")
    automation = ReviewAutomation(store)
    store.ensure_open("CR-1")

    state = automation.record_verification(
        "CR-1",
        {"valid": True},
        actor="system",
    )

    assert state["state"] == "DECISION_PENDING"
    assert state["can_apply_mutation"] is False


def test_invalid_verification_does_not_advance_to_verified(tmp_path):
    store = PersistentReviewStateStore(tmp_path / "states.jsonl")
    automation = ReviewAutomation(store)
    store.ensure_open("CR-2")

    try:
        automation.record_verification("CR-2", {"valid": False}, actor="system")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid evidence must be rejected")

    assert store.snapshot("CR-2")["state"] == "EVIDENCE_PENDING"
