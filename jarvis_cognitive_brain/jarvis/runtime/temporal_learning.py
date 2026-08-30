"""Temporal filtering and snapshot evaluation for learning cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Mapping, Any

from .learning_dedup import LearningCase


def _parse(value: str | date | datetime | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed.replace(tzinfo=None)


def _leq(left: str | datetime | None, right: datetime | None) -> bool:
    parsed = _parse(left)
    return right is None or parsed is None or parsed <= right


def observation_visible_at(
    observation: Mapping[str, Any],
    *,
    as_of: str | date | datetime | None = None,
    known_as_of: str | date | datetime | None = None,
) -> bool:
    observed = observation.get("observed_at") or observation.get("knowledge_time")
    knowledge = observation.get("knowledge_time") or observed
    return _leq(observed, _parse(as_of)) and _leq(knowledge, _parse(known_as_of))


def snapshot_case(
    case: LearningCase,
    *,
    as_of: str | date | datetime | None = None,
    known_as_of: str | date | datetime | None = None,
) -> LearningCase | None:
    """Rebuild a case from only observations visible in the requested snapshot."""
    visible = case.snapshot_observations(as_of=as_of, known_as_of=known_as_of)
    if not visible:
        return None
    rebuilt = LearningCase(
        case_id=case.case_id,
        fingerprint=case.fingerprint,
        goal=case.goal,
        lesson=case.lesson,
        risk=case.risk,
    )
    for item in visible:
        rebuilt.add(item)
    return rebuilt


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
    """Return reconstructed cases known by a historical point without leakage."""
    as_dt = _parse(as_of)
    known_dt = _parse(known_as_of)
    included: list[LearningCase] = []
    excluded: list[str] = []

    for case in cases:
        snap = snapshot_case(case, as_of=as_dt, known_as_of=known_dt)
        if snap is None:
            excluded.append(case.case_id)
            continue
        included.append(snap)

    snapshot = LearningSnapshot(
        as_of=as_dt.isoformat() if as_dt else None,
        known_as_of=known_dt.isoformat() if known_dt else None,
        included_case_ids=tuple(case.case_id for case in included),
        excluded_case_ids=tuple(excluded),
    )
    return included, snapshot
