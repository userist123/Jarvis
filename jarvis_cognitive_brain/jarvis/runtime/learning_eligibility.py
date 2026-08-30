"""Deterministic eligibility policy for reflection-driven learning candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class LearningEligibility:
    eligible: bool
    reasons: tuple[str, ...]
    risk: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "reasons": list(self.reasons),
            "risk": self.risk,
        }


def assess_learning_eligibility(observation: Mapping[str, Any]) -> LearningEligibility:
    """Decide whether an execution is worth reflection; never creates memory."""
    status = str(observation.get("status", "unknown"))
    evidence = observation.get("evidence_ids") or ()
    evidence_count = len(evidence) if not isinstance(evidence, (str, bytes)) else 1
    reasons: list[str] = []

    if status in {"success", "error", "blocked"}:
        reasons.append(f"execution status={status}")
    else:
        reasons.append("execution status is not reflection-eligible")

    if evidence_count:
        reasons.append(f"evidence_count={evidence_count}")

    risky = bool(observation.get("risky_capability")) or status == "blocked"
    risk = "high" if risky else ("medium" if status == "error" else "low")
    eligible = status in {"success", "error", "blocked"}
    return LearningEligibility(eligible=eligible, reasons=tuple(reasons), risk=risk)
