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
    counts = case.outcome_counts
    total = sum(counts.values()) or case.occurrences
    successes = counts.get("success", 0)
    errors = counts.get("error", 0)
    blocked = counts.get("blocked", 0)
    success_ratio = successes / total if total else 0.0
    failure_ratio = (errors + blocked) / total if total else 0.0
    outcome = max(0.0, min(1.0, success_ratio - 0.5 * failure_ratio))
    evidence = min(len(case.evidence_ids) / 3.0, 1.0)
    diversity = min(len(case.evidence_ids) / max(case.occurrences, 1), 1.0)
    penalty = {"low": 0.0, "medium": 0.15, "high": 0.35}.get(case.risk, 0.25)
    score = max(0.0, min(1.0, 0.35 * frequency + 0.30 * outcome + 0.20 * evidence + 0.15 * diversity - penalty))
    reasons = [
        f"occurrences={case.occurrences}",
        f"outcome_counts={dict(sorted(counts.items()))}",
        f"evidence={len(case.evidence_ids)}",
    ]
    if penalty:
        reasons.append(f"risk_penalty={penalty}")
    promotable = (
        score >= 0.75
        and case.occurrences >= 3
        and len(case.evidence_ids) >= 2
        and success_ratio >= 0.8
        and case.risk == "low"
    )
    if not promotable:
        reasons.append("promotion criteria not satisfied")
    return LearningConfidence(score, frequency, outcome, evidence, diversity, penalty, promotable, tuple(reasons))
