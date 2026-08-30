from jarvis.runtime.conflict_reviewer_ui import ConflictReviewerWindow
from jarvis.runtime.reviewer_identity import ReviewerIdentity, ReviewerPrincipal


def test_conflict_reviewer_requires_identity_context():
    identity = ReviewerIdentity.unauthenticated()
    assert identity.principal is ReviewerPrincipal.UNAUTHENTICATED
    assert identity.can_decide is False
    assert ConflictReviewerWindow.__doc__


def test_authenticated_human_can_decide():
    identity = ReviewerIdentity(
        subject="DOMAIN\\alice",
        principal=ReviewerPrincipal.HUMAN,
        authenticated=True,
    )
    assert identity.can_decide is True
