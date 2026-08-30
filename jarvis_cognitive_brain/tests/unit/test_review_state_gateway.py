import pytest

from jarvis.runtime.conflict_review import ConflictReviewService


class FakeBackend:
    principal = "human"
    controller = object()


class FakeBridge:
    available = True
    _backend = FakeBackend()


def test_apply_verdict_requires_review_state(monkeypatch):
    service = ConflictReviewService(FakeBridge())

    class FakeGate:
        def __init__(self, controller):
            pass

        def apply(self, **kwargs):
            assert kwargs["review_state"]["state"] == "APPROVED"
            return type("R", (), {"as_dict": lambda self: {"changed": True}})()

    monkeypatch.setattr(
        "memory_controller.mutation_gate.MutationGate",
        FakeGate,
    )

    verdict = {
        "verdict_id": "V-1",
        "verdict": "ACCEPT_A",
        "reviewer": "operator",
        "reviewer_principal": "human",
        "memory_ids": ["A", "B"],
        "evidence_bundle_hash": "e" * 64,
        "as_of": None,
        "known_as_of": None,
        "evidence_valid": True,
        "reason": "reviewed",
        "issued_at": "2026-08-30T10:00:00+00:00",
    }
    verification = {
        "valid": True,
        "bundle_hash_matches": True,
        "bundle_hash": "e" * 64,
        "stale_memory_ids": [],
        "missing_memory_ids": [],
        "bundle_id": "EB-1",
    }
    result = service.apply_verdict(
        principal="human",
        verdict=verdict,
        evidence_verification=verification,
        review_state={"state": "APPROVED", "can_apply_mutation": True},
        action="attest",
        reason="reviewed",
    )
    assert result["changed"] is True
