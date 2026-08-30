"""Authenticated reviewer operations for JARVIS governance workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .reviewer_identity import ReviewerIdentity


@dataclass(frozen=True)
class AuthenticatedReviewer:
    """Bind reviewer operations to an authenticated identity context."""

    identity: ReviewerIdentity
    gateway: Any

    def _require_decision(self) -> None:
        if not self.identity.can_decide:
            raise PermissionError("Authenticated HUMAN/ADMIN reviewer identity is required")

    def issue_conflict_verdict(
        self,
        *,
        verdict: str,
        memory_ids: Iterable[str],
        evidence_bundle_hash: str,
        evidence_valid: bool,
        reason: str,
        as_of: Any = None,
        known_as_of: Any = None,
    ) -> dict[str, Any]:
        self._require_decision()
        return self.gateway.issue_conflict_verdict(
            principal=self.identity.principal.value,
            reviewer=self.identity.subject,
            verdict=verdict,
            memory_ids=tuple(memory_ids),
            evidence_bundle_hash=evidence_bundle_hash,
            evidence_valid=evidence_valid,
            reason=reason,
            as_of=as_of,
            known_as_of=known_as_of,
        )

    def apply_conflict_verdict(
        self,
        *,
        verdict: dict[str, Any],
        evidence_verification: dict[str, Any],
        review_state: dict[str, Any],
        action: str,
        reason: str,
    ) -> dict[str, Any]:
        self._require_decision()
        return self.gateway.apply_conflict_verdict(
            principal=self.identity.principal.value,
            verdict=verdict,
            evidence_verification=evidence_verification,
            review_state=review_state,
            action=action,
            reason=reason,
        )

    def promote_learning_candidate(
        self,
        *,
        memory_id: str,
        evidence_verification: dict[str, Any],
        evidence_bundle_hash: str,
        confidence: dict[str, Any],
        confidence_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_decision()
        return self.gateway.promote_learning_candidate(
            principal=self.identity.principal.value,
            reviewer=self.identity.subject,
            memory_id=memory_id,
            evidence_verification=evidence_verification,
            evidence_bundle_hash=evidence_bundle_hash,
            confidence=confidence,
            confidence_snapshot=confidence_snapshot,
        )

    def transition_review_state(self, *, case_id: str, target: str, reason: str) -> dict[str, Any]:
        self._require_decision()
        return self.gateway.transition_review_state(
            case_id=case_id,
            target=target,
            actor=self.identity.subject,
            reason=reason,
        )
