from jarvis.runtime.reviewer_identity import ReviewerIdentity, ReviewerPrincipal


def test_unauthenticated_identity_cannot_decide():
    identity = ReviewerIdentity.unauthenticated()
    assert identity.authenticated is False
    assert identity.can_decide is False


def test_human_identity_can_decide():
    identity = ReviewerIdentity(subject="operator-1", principal=ReviewerPrincipal.HUMAN, authenticated=True)
    assert identity.authenticated is True
    assert identity.can_decide is True


def test_ai_agent_cannot_decide():
    identity = ReviewerIdentity(subject="jarvis", principal=ReviewerPrincipal.AI_AGENT, authenticated=True)
    assert identity.can_decide is False
