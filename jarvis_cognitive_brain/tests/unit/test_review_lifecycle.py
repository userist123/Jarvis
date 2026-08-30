from jarvis.runtime.review_lifecycle import ReviewLifecycleService
from jarvis.runtime.review_state_store import PersistentReviewStateStore


def test_auto_advance_only_to_decision_pending(tmp_path):
    store = PersistentReviewStateStore(tmp_path / "states.jsonl")
    store.ensure_open("CR-1")
    service = ReviewLifecycleService(store)

    result = service.auto_advance_after_evidence(
        "CR-1",
        evidence_verification={"valid": True},
    )

    assert result.state["state"] == "DECISION_PENDING"
    assert "APPROVED" not in result.advanced


def test_invalid_evidence_stops_at_pending(tmp_path):
    store = PersistentReviewStateStore(tmp_path / "states.jsonl")
    store.ensure_open("CR-2")
    service = ReviewLifecycleService(store)

    result = service.auto_advance_after_evidence(
        "CR-2",
        evidence_verification={"valid": False},
    )

    assert result.state["state"] == "EVIDENCE_PENDING"


def test_close_requires_terminal_decision(tmp_path):
    store = PersistentReviewStateStore(tmp_path / "states.jsonl")
    store.ensure_open("CR-3")
    service = ReviewLifecycleService(store)

    service.record_decision("CR-3", decision="DEFERRED", actor="reviewer", reason="Need more evidence")
    closed = service.close("CR-3", actor="reviewer", reason="Case closed")

    assert closed["state"] == "CLOSED"
