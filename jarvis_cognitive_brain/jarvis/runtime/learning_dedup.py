"""Deterministic deduplication and aggregation for reflection candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Mapping


def _normalize(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[.!?]+$", "", text)
    return text


@dataclass
class LearningCase:
    case_id: str
    fingerprint: str
    goal: str
    lesson: str
    risk: str
    occurrences: int = 0
    evidence_ids: set[str] = field(default_factory=set)
    execution_ids: set[str] = field(default_factory=set)
    statuses: set[str] = field(default_factory=set)
    outcome_counts: dict[str, int] = field(default_factory=dict)

    def add(self, observation: Mapping[str, Any]) -> None:
        self.occurrences += 1
        self.evidence_ids.update(str(x) for x in (observation.get("evidence_ids") or ()) if x)
        execution_id = observation.get("execution_id")
        if execution_id:
            self.execution_ids.add(str(execution_id))
        status = observation.get("status")
        if status:
            normalized = str(status)
            self.statuses.add(normalized)
            self.outcome_counts[normalized] = self.outcome_counts.get(normalized, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "fingerprint": self.fingerprint,
            "goal": self.goal,
            "lesson": self.lesson,
            "risk": self.risk,
            "occurrences": self.occurrences,
            "evidence_ids": sorted(self.evidence_ids),
            "execution_ids": sorted(self.execution_ids),
            "statuses": sorted(self.statuses),
            "outcome_counts": dict(sorted(self.outcome_counts.items())),
        }


def fingerprint_learning(goal: str, lesson: str) -> str:
    payload = json.dumps(
        {"goal": _normalize(goal), "lesson": _normalize(lesson)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LearningDeduplicator:
    def __init__(self) -> None:
        self._cases: dict[str, LearningCase] = {}

    def record(
        self,
        *,
        goal: str,
        lesson: str,
        risk: str,
        observation: Mapping[str, Any],
    ) -> LearningCase:
        fingerprint = fingerprint_learning(goal, lesson)
        case = self._cases.get(fingerprint)
        if case is None:
            case = LearningCase(
                case_id=f"LC-{fingerprint[:16]}",
                fingerprint=fingerprint,
                goal=goal,
                lesson=lesson,
                risk=risk,
            )
            self._cases[fingerprint] = case
        case.add(observation)
        if risk == "high" or case.risk == "high":
            case.risk = "high"
        elif risk == "medium" and case.risk == "low":
            case.risk = "medium"
        return case

    def get(self, fingerprint: str) -> LearningCase | None:
        return self._cases.get(fingerprint)

    def all(self) -> list[LearningCase]:
        return list(self._cases.values())
