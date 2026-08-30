import pytest

from jarvis.runtime.authenticated_reviewer import AuthenticatedReviewer
from jarvis.runtime.reviewer_identity import ReviewerIdentity, ReviewerPrincipal


class SpyGateway:
    def __init__(self):
        self.calls = []

    def issue_conflict_verdict(self, **kwargs):
        self.calls.append(("issue", kwargs))
        return kwargs

    def promote_learning_candidate(self, **kwargs):
        self.calls.append(("promote", kwargs))
        return kwargs

    def transition_review_state(self, **kwargs):
        self.calls.append(("transition", kwargs))
        return kwargs


def test_unauthenticated_reviewer_is_denied():
    gateway = SpyGateway()
    reviewer = AuthenticatedReviewer(ReviewerIdentity.unauthenticated(), gateway)
    with pytest.raises(PermissionError):
        reviewer.issue_conflict_verdict(
            verdict="ACCEPT_A",
            memory_ids=("A", "B"),
            evidence_bundle_hash="hash",
            evidence_valid=True,
            reason="reason",
        )
    assert gateway.calls == []


def test_ai_agent_is_denied():
    gateway = SpyGateway()
    identity = ReviewerIdentity(
        subject="agent",
        principal=ReviewerPrincipal.AI_AGENT,
        authenticated=True,
    )
    reviewer = AuthenticatedReviewer(identity, gateway)
    with pytest.raises(PermissionError):
        reviewer.promote_learning_candidate(
            memory_id="M",
            evidence_verification={},
            evidence_bundle_hash="hash",
            confidence={"promotable": True, "score": 0.9},
            confidence_snapshot={"fingerprint": "fp"},
        )
    assert gateway.calls == []


def test_human_identity_is_bound_to_gateway_call():
    gateway = SpyGateway()
    identity = ReviewerIdentity(
        subject="DOMAIN\\alice",
        principal=ReviewerPrincipal.HUMAN,
        authenticated=True,
    )
    reviewer = AuthenticatedReviewer(identity, gateway)
    reviewer.issue_conflict_verdict(
        verdict="ACCEPT_A",
        memory_ids=("A", "B"),
        evidence_bundle_hash="hash",
        evidence_valid=True,
        reason="confirmed",
    )
    kind, kwargs = gateway.calls[-1]
    assert kind == "issue"
    assert kwargs["reviewer"] == "DOMAIN\\alice"
    assert kwargs["principal"] == "HUMAN"
