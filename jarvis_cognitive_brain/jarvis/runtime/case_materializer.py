"""Materialize memory-intelligence signals into canonical or provisional review work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .memory_case_store import MemoryCaseStore


@dataclass(frozen=True)
class MaterializationResult:
    signal_id: str
    kind: str
    route: str
    case_id: str
    canonical: bool
    status: str
    memory_ids: tuple[str, ...]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "kind": self.kind,
            "route": self.route,
            "case_id": self.case_id,
            "canonical": self.canonical,
            "status": self.status,
            "memory_ids": list(self.memory_ids),
            "metadata": dict(self.metadata),
        }


class CaseMaterializer:
    """Turn triaged signals into canonical conflict cases or provisional work items."""

    def __init__(self, case_store: MemoryCaseStore, conflict_service: Any | None = None) -> None:
        self.case_store = case_store
        self.conflict_service = conflict_service

    def materialize(self, signal: Mapping[str, Any]) -> MaterializationResult:
        signal_id = str(signal.get("signal_id") or "")
        if not signal_id:
            raise ValueError("signal_id is required")
        existing = self.case_store.get_by_signal(signal_id)
        signal_type = str(signal.get("signal_type") or "")
        memory_ids = tuple(str(x) for x in signal.get("memory_ids") or [] if str(x))

        if signal_type == "POTENTIAL_CONTRADICTION" and self.conflict_service is not None:
            canonical_case_id = str((existing or {}).get("canonical_case_id") or "")
            if not canonical_case_id:
                case = self.conflict_service.open_case(
                    memory_ids=memory_ids,
                    reasons=(str(signal.get("reason") or "Potential contradiction detected"),),
                    conflict_type="semantic",
                    evidence_ids=memory_ids,
                )
                canonical_case_id = str(case.get("case_id") or "")
                if not canonical_case_id:
                    raise RuntimeError("Canonical conflict case did not return case_id")
                provisional = self.case_store.create_from_signal(signal)
                self.case_store.attach_canonical_case(signal_id, canonical_case_id, status="OPEN")
            return MaterializationResult(
                signal_id=signal_id,
                kind="conflict",
                route="CONFLICT_REVIEW",
                case_id=canonical_case_id,
                canonical=True,
                status="OPEN",
                memory_ids=memory_ids,
                metadata={"materialization": "canonical_conflict_review"},
            )

        provisional = existing or self.case_store.create_from_signal(signal)
        route = str(provisional.get("route") or "UNROUTED")
        kind = str(provisional.get("kind") or "unknown")
        status = str(provisional.get("status") or "OPEN")
        return MaterializationResult(
            signal_id=signal_id,
            kind=kind,
            route=route,
            case_id=str(provisional.get("case_id") or ""),
            canonical=False,
            status=status,
            memory_ids=memory_ids,
            metadata={"materialization": "provisional_work_item"},
        )
