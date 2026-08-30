"""Controlled trigger for reflection-driven learning aggregation."""

from __future__ import annotations

from typing import Any, Mapping

from .learning_dedup import LearningCase, LearningDeduplicator
from .learning_eligibility import assess_learning_eligibility


class LearningTrigger:
    """Admits eligible observations into a deduplicated learning case."""

    def __init__(self, deduplicator: LearningDeduplicator | None = None) -> None:
        self.deduplicator = deduplicator or LearningDeduplicator()

    def observe(
        self,
        *,
        goal: str,
        lesson: str,
        observation: Mapping[str, Any],
    ) -> LearningCase | None:
        eligibility = assess_learning_eligibility(observation)
        if not eligibility.eligible:
            return None
        return self.deduplicator.record(
            goal=goal,
            lesson=lesson,
            risk=eligibility.risk,
            observation=observation,
        )
