"""Policy-aware reviewer action model for the JARVIS UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ReviewerActions:
    inspect: bool
    verify_evidence: bool
    approve: bool
    reject: bool
    defer: bool
    close: bool
    mutate: bool
    reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "inspect": self.inspect,
            "verify_evidence": self.verify_evidence,
            "approve": self.approve,
            "reject": self.reject,
            "defer": self.defer,
            "close": self.close,
            "mutate": self.mutate,
            "reasons": list(self.reasons),
        }


def derive_reviewer_actions(
    *,
    review_state: Mapping[str, Any],
    evidence_verification: Mapping[str, Any] | None = None,
    principal: str = "HUMAN",
    confidence: Mapping[str, Any] | None = None,
) -> ReviewerActions:
    """Return UI affordances only; authoritative gates remain in the Vault."""
    state = str(review_state.get("state") or "")
    can_mutate = review_state.get("can_apply_mutation") is True
    evidence = evidence_verification or {}
    valid_evidence = evidence.get("valid") is True and evidence.get("bundle_hash_matches") is True
    is_reviewer = principal in {"HUMAN", "ADMIN"}
    promotable = (confidence or {}).get("promotable") is True

    reasons: list[str] = []
    approve = state == "DECISION_PENDING" and is_reviewer
    reject = approve
    defer = state in {"OPEN", "EVIDENCE_PENDING", "VERIFIED", "DECISION_PENDING"} and is_reviewer
    close = state in {"APPROVED", "REJECTED", "DEFERRED"} and is_reviewer
    verify = state == "EVIDENCE_PENDING"
    mutate = state == "APPROVED" and can_mutate and valid_evidence and is_reviewer

    if not is_reviewer:
        reasons.append("Principal is not authorized for reviewer decisions")
    if state != "APPROVED":
        reasons.append("Mutation requires APPROVED review state")
    if not valid_evidence:
        reasons.append("Verified evidence is required for mutation")
    if confidence is not None and not promotable:
        reasons.append("Confidence criteria are not promotable")

    return ReviewerActions(
        inspect=True,
        verify_evidence=verify,
        approve=approve,
        reject=reject,
        defer=defer,
        close=close,
        mutate=mutate,
        reasons=tuple(dict.fromkeys(reasons)),
    )
