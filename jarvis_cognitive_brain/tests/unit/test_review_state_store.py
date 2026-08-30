from pathlib import Path

from jarvis.runtime.review_state import ReviewState
from jarvis.runtime.review_state_store import PersistentReviewStateStore


def test_review_state_survives_restart(tmp_path: Path):
    path = tmp_path / "review_states.jsonl"
    first = PersistentReviewStateStore(path)
    first.ensure_open("CR-1")
    first.transition("CR-1", ReviewState.EVIDENCE_PENDING, actor="alice", reason="collect evidence")
    first.transition("CR-1", ReviewState.VERIFIED, actor="alice", reason="evidence verified")

    second = PersistentReviewStateStore(path)
    assert second.snapshot("CR-1")["state"] == ReviewState.VERIFIED.value


def test_invalid_transition_is_fail_closed(tmp_path: Path):
    store = PersistentReviewStateStore(tmp_path / "review_states.jsonl")
    store.ensure_open("CR-2")
    try:
        store.transition("CR-2", ReviewState.APPROVED, actor="alice", reason="skip")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid state transition must be rejected")
