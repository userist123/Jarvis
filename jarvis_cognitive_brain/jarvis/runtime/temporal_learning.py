"""Temporal filtering and snapshot evaluation for learning cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from .learning_dedup import LearningCase


def _parse(value: str | date | datetime | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed.replace(tzinfo=None)


def _leq(left: str, right: datetime | None) -> bool:
    parsed = _parse(left)
    return right is None or parsed is None or parsed <= right


@dataclass(frozen=True)
class LearningSnapshot:
    as_of: str | None
    known_as_of: str | None
    included_case_ids: tuple[str, ...]
    excluded_case_ids: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "as_of": self.as_of,
            "known_as_of": self.known_as_of,
            "included_case_ids": list(self.included_case_ids),
            "excluded_case_ids": list(self.excluded_case_ids),
        }


def filter_learning_cases(
    cases: Iterable[LearningCase],
    *,
    as_of: str | date | datetime | None = None,
    known_as_of: str | date | datetime | None = None,
) -> tuple[list[LearningCase], LearningSnapshot]:
    """Return cases known by a historical point without retroactive leakage."""
    as_dt = _parse(as_of)
    known_dt = _parse(known_as_of)
    included: list[LearningCase] = []
    excluded: list[str] = []

    for case in cases:
        if as_dt is not None and case.first_observed_at and not _leq(case.first_observed_at, as_dt):
            excluded.append(case.case_id)
            continue
        if known_dt is not None and case.first_observed_at and not _leq(case.first_observed_at, known_dt):
            excluded.append(case.case_id)
            continue
        included.append(case)

    snapshot = LearningSnapshot(
        as_of=as_dt.isoformat() if as_dt else None,
        known_as_of=known_dt.isoformat() if known_dt else None,
        included_case_ids=tuple(case.case_id for case in included),
        excluded_case_ids=tuple(excluded),
    )
    return included, snapshot
