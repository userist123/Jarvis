"""Controlled lifecycle orchestration for JARVIS review cases.

Only deterministic transitions are automated. Approval/rejection decisions remain
explicit reviewer actions, and closure requires a completed terminal outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .review_state_store import PersistentReviewStateStore


@dataclass(frozen=True)
class LifecycleResult:
    case_id: str
    state: dict[str, Any]
    advanced: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "state": self.state,
            "advanced": list(self.advanced),
        }


class ReviewLifecycleService:
    """Apply safe workflow transitions and enforce terminal closure rules."""

    def __init__(self, store: PersistentReviewStateStore | None = None) -> None:
        self.store = store or PersistentReviewStateStore()

    def auto_advance_after_evidence(
        self,
        case_id: str,
        *,
        evidence_verification: Mapping[str, Any],
        actor: str = "system",
    ) -> LifecycleResult:
        state = self.store.snapshot(case_id)
        advanced: list[str] = []
        current = str(state.get("state", ""))

        if current == "OPEN":
            self.store.transition(case_id, "EVIDENCE_PENDING", actor=actor, reason="Evidence acquisition started")
            advanced.append("EVIDENCE_PENDING")
            current = "EVIDENCE_PENDING"

        if current == "EVIDENCE_PENDING":
            if not evidence_verification.get("valid"):
                return LifecycleResult(case_id, self.store.snapshot(case_id), tuple(advanced))
            self.store.transition(case_id, "VERIFIED", actor=actor, reason="Evidence verification passed")
            advanced.append("VERIFIED")
            current = "VERIFIED"

        if current == "VERIFIED":
            self.store.transition(case_id, "DECISION_PENDING", actor=actor, reason="Verified evidence is ready for reviewer decision")
            advanced.append("DECISION_PENDING")

        return LifecycleResult(case_id, self.store.snapshot(case_id), tuple(advanced))

    def record_decision(self, case_id: str, *, decision: str, actor: str, reason: str) -> dict[str, Any]:
        normalized = str(decision).upper().strip()
        target = {
            "APPROVED": "APPROVED",
            "REJECTED": "REJECTED",
            "DEFERRED": "DEFERRED",
        }.get(normalized)
        if target is None:
            raise ValueError("decision must be APPROVED, REJECTED, or DEFERRED")
        return self.store.transition(case_id, target, actor=actor, reason=reason).as_dict()

    def close(self, case_id: str, *, actor: str, reason: str) -> dict[str, Any]:
        state = self.store.snapshot(case_id)
        if state.get("state") not in {"APPROVED", "REJECTED", "DEFERRED"}:
            raise ValueError("Only a terminal decision state can be closed")
        transition = self.store.transition(case_id, "CLOSED", actor=actor, reason=reason)
        return {**self.store.snapshot(case_id), "transition": transition.as_dict()}
