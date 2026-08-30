"""Unified lifecycle contract for governance work items."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    VERIFIED = "VERIFIED"
    DECISION_PENDING = "DECISION_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class UnifiedCase:
    case_id: str
    kind: str
    route: str
    status: CaseStatus
    source_signal_id: str | None = None
    canonical_case_id: str | None = None
    memory_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "kind": self.kind,
            "route": self.route,
            "status": self.status.value,
            "source_signal_id": self.source_signal_id,
            "canonical_case_id": self.canonical_case_id,
            "memory_ids": list(self.memory_ids),
            "metadata": dict(self.metadata or {}),
        }


_AUTO_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.OPEN: {CaseStatus.EVIDENCE_PENDING},
    CaseStatus.EVIDENCE_PENDING: {CaseStatus.VERIFIED},
    CaseStatus.VERIFIED: {CaseStatus.DECISION_PENDING},
}

_DECISION_TRANSITIONS = {
    CaseStatus.DECISION_PENDING: {
        CaseStatus.APPROVED,
        CaseStatus.REJECTED,
        CaseStatus.DEFERRED,
    }
}

_FINAL_TRANSITIONS = {
    CaseStatus.APPROVED: {CaseStatus.CLOSED},
    CaseStatus.REJECTED: {CaseStatus.CLOSED},
    CaseStatus.DEFERRED: {CaseStatus.CLOSED},
}


def validate_transition(current: CaseStatus, target: CaseStatus, *, automated: bool = False) -> None:
    if current == target:
        return
    allowed = _AUTO_TRANSITIONS.get(current, set()) if automated else set()
    if not automated:
        allowed = set(_AUTO_TRANSITIONS.get(current, set())) | set(_DECISION_TRANSITIONS.get(current, set())) | set(_FINAL_TRANSITIONS.get(current, set()))
    if target not in allowed:
        raise ValueError(f"Invalid case transition: {current.value} -> {target.value}")


def can_apply_mutation(status: CaseStatus, *, action: str) -> bool:
    if status is not CaseStatus.APPROVED:
        return False
    return action not in {"none", "defer"}
