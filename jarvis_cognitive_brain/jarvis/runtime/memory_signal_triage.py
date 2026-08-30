"""Deterministic triage for memory-intelligence signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class TriageDecision:
    signal_id: str
    signal_type: str
    route: str
    priority: str
    severity: str
    confidence: float
    reason: str
    recommended_actions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "route": self.route,
            "priority": self.priority,
            "severity": self.severity,
            "confidence": self.confidence,
            "reason": self.reason,
            "recommended_actions": list(self.recommended_actions),
            "read_only": True,
        }


def _priority(signal_type: str, severity: str, confidence: float) -> str:
    if signal_type == "POTENTIAL_CONTRADICTION" or severity == "critical":
        return "urgent"
    if severity == "high" or confidence >= 0.95:
        return "high"
    if severity == "medium" or confidence >= 0.75:
        return "normal"
    return "low"


def triage_signal(signal: Mapping[str, Any]) -> TriageDecision:
    signal_type = str(signal.get("signal_type") or "UNKNOWN")
    severity = str(signal.get("severity") or "low")
    confidence = max(0.0, min(1.0, float(signal.get("confidence", 0.0))))
    if signal_type == "POTENTIAL_CONTRADICTION":
        route = "CONFLICT_REVIEW"
        actions = ("OPEN_CONFLICT_REVIEW", "VERIFY_EVIDENCE")
        reason = "Potential contradiction requires semantic evidence verification."
    elif signal_type == "DUPLICATE":
        route = "LEARNING_REVIEW"
        actions = ("OPEN_MEMORY_REVIEW", "COMPARE_MEMORIES")
        reason = "Duplicate candidate requires human review before merge or archival."
    elif signal_type == "STALE":
        route = "MEMORY_REVIEW"
        actions = ("OPEN_MEMORY_REVIEW", "REQUEST_REVALIDATION")
        reason = "Stale memory requires revalidation before any replacement."
    elif signal_type == "KNOWLEDGE_GAP":
        route = "KNOWLEDGE_ACQUISITION"
        actions = ("OPEN_MEMORY_REVIEW", "REQUEST_EVIDENCE")
        reason = "Knowledge gap should trigger evidence acquisition rather than mutation."
    else:
        route = "MANUAL_REVIEW"
        actions = ("OPEN_MEMORY_REVIEW",)
        reason = "Unknown signal type requires manual triage."
    return TriageDecision(
        signal_id=str(signal.get("signal_id") or ""),
        signal_type=signal_type,
        route=route,
        priority=_priority(signal_type, severity, confidence),
        severity=severity,
        confidence=confidence,
        reason=reason,
        recommended_actions=actions,
    )


def triage_signals(signals: Iterable[Mapping[str, Any]]) -> list[TriageDecision]:
    decisions = [triage_signal(signal) for signal in signals]
    rank = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
    decisions.sort(key=lambda item: (rank.get(item.priority, 9), -item.confidence, item.signal_id))
    return decisions
