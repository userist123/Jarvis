"""Derived review queue for persistent JARVIS learning cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .learning_confidence import LearningConfidence, assess_learning_confidence
from .learning_dedup import LearningCase


_RISK_PRIORITY = {"high": 3, "medium": 2, "low": 1}


@dataclass(frozen=True)
class LearningReviewItem:
    case_id: str
    risk: str
    confidence_score: float
    promotable: bool
    occurrences: int
    evidence_count: int
    priority: float
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "risk": self.risk,
            "confidence_score": round(self.confidence_score, 4),
            "promotable": self.promotable,
            "occurrences": self.occurrences,
            "evidence_count": self.evidence_count,
            "priority": round(self.priority, 4),
            "reasons": list(self.reasons),
        }


def build_review_item(case: LearningCase, confidence: LearningConfidence | None = None) -> LearningReviewItem:
    confidence = confidence or assess_learning_confidence(case)
    risk_weight = _RISK_PRIORITY.get(case.risk, 2)
    priority = risk_weight * 0.45 + confidence.score * 0.35 + min(case.occurrences / 5.0, 1.0) * 0.20
    reasons = list(confidence.reasons)
    if case.risk == "high":
        reasons.append("high-risk case requires review")
    return LearningReviewItem(
        case_id=case.case_id,
        risk=case.risk,
        confidence_score=confidence.score,
        promotable=confidence.promotable,
        occurrences=case.occurrences,
        evidence_count=len(case.evidence_ids),
        priority=priority,
        reasons=tuple(reasons),
    )


class LearningReviewQueue:
    """Build a deterministic, read-only queue from persistent learning cases."""

    def build(self, cases: list[LearningCase]) -> list[LearningReviewItem]:
        items = [build_review_item(case) for case in cases]
        return sorted(items, key=lambda item: (-item.priority, item.case_id))
