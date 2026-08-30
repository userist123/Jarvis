"""Confidence evaluation over temporally reconstructed learning cases."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from .learning_confidence import LearningConfidence, assess_learning_confidence
from .learning_dedup import LearningCase
from .temporal_learning import LearningSnapshot, filter_learning_cases


def assess_temporal_learning_confidence(
    cases: Iterable[LearningCase],
    *,
    as_of: str | date | datetime | None = None,
    known_as_of: str | date | datetime | None = None,
) -> tuple[list[tuple[LearningCase, LearningConfidence]], LearningSnapshot]:
    """Score only observations visible in the requested temporal snapshot."""
    visible, snapshot = filter_learning_cases(cases, as_of=as_of, known_as_of=known_as_of)
    return [(case, assess_learning_confidence(case)) for case in visible], snapshot
