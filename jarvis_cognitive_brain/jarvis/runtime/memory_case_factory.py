"""Idempotent conversion of memory-intelligence signals into review work items."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True)
class MemoryCaseRef:
    case_id: str
    kind: str
    signal_id: str
    status: str
    route: str
    created_at: str
    memory_ids: tuple[str, ...]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "kind": self.kind,
            "signal_id": self.signal_id,
            "status": self.status,
            "route": self.route,
            "created_at": self.created_at,
            "memory_ids": list(self.memory_ids),
            "metadata": dict(self.metadata),
        }


def _kind_route(signal_type: str) -> tuple[str, str]:
    mapping = {
        "POTENTIAL_CONTRADICTION": ("conflict", "CONFLICT_REVIEW"),
        "DUPLICATE": ("learning", "LEARNING_REVIEW"),
        "STALE": ("memory", "MEMORY_REVIEW"),
        "KNOWLEDGE_GAP": ("acquisition", "KNOWLEDGE_ACQUISITION"),
    }
    return mapping.get(signal_type, ("unknown", "UNROUTED"))


class MemoryCaseFactory:
    """Create stable case references without mutating canonical memory."""

    def __init__(self, existing: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        self._by_signal = {str(k): dict(v) for k, v in (existing or {}).items()}

    def create_from_signal(self, signal: Mapping[str, Any]) -> dict[str, Any]:
        signal_id = str(signal.get("signal_id") or "")
        if not signal_id:
            raise ValueError("signal_id is required")
        existing = self._by_signal.get(signal_id)
        if existing:
            return dict(existing)

        signal_type = str(signal.get("signal_type") or "")
        kind, route = _kind_route(signal_type)
        case_id = f"MC-{signal_id}"
        item = MemoryCaseRef(
            case_id=case_id,
            kind=kind,
            signal_id=signal_id,
            status="OPEN",
            route=route,
            created_at=datetime.now(timezone.utc).isoformat(),
            memory_ids=tuple(str(x) for x in signal.get("memory_ids") or [] if str(x)),
            metadata={
                "severity": signal.get("severity"),
                "confidence": signal.get("confidence"),
                "reason": signal.get("reason"),
                "signal_metadata": dict(signal.get("metadata") or {}),
            },
        ).as_dict()
        self._by_signal[signal_id] = dict(item)
        return item

    def all(self) -> list[dict[str, Any]]:
        return [dict(self._by_signal[k]) for k in sorted(self._by_signal)]
