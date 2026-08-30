"""Explainable confidence and promotion criteria for learning cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .learning_dedup import LearningCase


@dataclass(frozen=True)
class LearningConfidence:
    score: float
    frequency_score: float
    outcome_score: float
    evidence_score: float
    diversity_score: float
    risk_penalty: float
    promotable: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "frequency_score": round(self.frequency_score, 4),
            "outcome_score": round(self.outcome_score, 4),
            "evidence_score": round(self.evidence_score, 4),
            "diversity_score": round(self.diversity_score, 4),
            "risk_penalty": round(self.risk_penalty, 4),
            "promotable": self.promotable,
            "reasons": list(self.reasons),
        }


def assess_learning_confidence(case: LearningCase) -> LearningConfidence:
    frequency = min(case.occurrences / 5.0, 1.0)
    successes = sum(1 for status in case.statuses if status == "success")
    errors = sum(1 for status in case.statuses if status == "error")
    blocked = sum(1 for status in case.statuses if status == "blocked")
    outcome = 1.0 if successes and not errors and not blocked else 0.5 if successes else 0.25
    evidence = min(len(case.evidence_ids) / 3.0, 1.0)
    diversity = min(len(case.statuses) / 2.0, 1.0) if case.statuses else 0.0
    penalty = {"low": 0.0, "medium": 0.15, "high": 0.35}.get(case.risk, 0.25)
    score = max(0.0, min(1.0, 0.35 * frequency + 0.30 * outcome + 0.20 * evidence + 0.15 * diversity - penalty))
    reasons = [f"occurrences={case.occurrences}", f"evidence={len(case.evidence_ids)}", f"statuses={sorted(case.statuses)}"]
    if penalty:
        reasons.append(f"risk_penalty={penalty}")
    promotable = score >= 0.75 and case.occurrences >= 3 and len(case.evidence_ids) >= 2 and case.risk == "low"
    if not promotable:
        reasons.append("promotion criteria not satisfied")
    return LearningConfidence(score, frequency, outcome, evidence, diversity, penalty, promotable, tuple(reasons))
