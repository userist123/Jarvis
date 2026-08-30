"""Safe automation for non-decisional review-state transitions."""

from __future__ import annotations

from typing import Any, Mapping

from .review_state_store import PersistentReviewStateStore


class ReviewAutomation:
    """Advance only deterministic, non-approval review states."""

    def __init__(self, store: PersistentReviewStateStore | None = None) -> None:
        self.store = store or PersistentReviewStateStore()

    def begin_evidence(self, case_id: str, *, actor: str = "system") -> dict[str, Any]:
        state = self.store.snapshot(case_id)
        if state.get("state") == "OPEN":
            self.store.transition(case_id, "EVIDENCE_PENDING", actor=actor, reason="Evidence acquisition started")
        return self.store.snapshot(case_id)

    def record_verification(
        self,
        case_id: str,
        verification: Mapping[str, Any],
        *,
        actor: str = "system",
    ) -> dict[str, Any]:
        state = self.store.snapshot(case_id)
        current = state.get("state")
        if current == "OPEN":
            self.store.transition(case_id, "EVIDENCE_PENDING", actor=actor, reason="Evidence verification requested")
            current = "EVIDENCE_PENDING"
        if current != "EVIDENCE_PENDING":
            raise ValueError(f"Evidence verification requires EVIDENCE_PENDING state, got {current!r}")
        if not verification.get("valid"):
            raise ValueError("Invalid evidence cannot advance review state")
        self.store.transition(case_id, "VERIFIED", actor=actor, reason="Evidence verification passed")
        self.store.transition(case_id, "DECISION_PENDING", actor=actor, reason="Verified evidence is ready for reviewer decision")
        return self.store.snapshot(case_id)

    def advance_safe(
        self,
        case_id: str,
        *,
        verification: Mapping[str, Any] | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        state = self.store.snapshot(case_id)
        if state.get("state") == "OPEN":
            self.begin_evidence(case_id, actor=actor)
        if verification is not None:
            return self.record_verification(case_id, verification, actor=actor)
        return self.store.snapshot(case_id)
