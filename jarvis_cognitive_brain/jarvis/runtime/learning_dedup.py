"""Deterministic deduplication and aggregation for reflection candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping


def _normalize(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[.!?]+$", "", text)
    return text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    first_observed_at: str = ""
    last_observed_at: str = ""
    knowledge_times: set[str] = field(default_factory=set)
    observations: list[dict[str, Any]] = field(default_factory=list)

    def add(self, observation: Mapping[str, Any]) -> None:
        observed_at = str(observation.get("observed_at") or _now())
        known_at = observation.get("known_as_of") or observation.get("knowledge_time") or observed_at
        status = str(observation.get("status") or "unknown")
        evidence = tuple(str(x) for x in (observation.get("evidence_ids") or ()) if x)
        execution_id = str(observation.get("execution_id") or "")

        self.occurrences += 1
        self.evidence_ids.update(evidence)
        if execution_id:
            self.execution_ids.add(execution_id)
        self.statuses.add(status)
        self.outcome_counts[status] = self.outcome_counts.get(status, 0) + 1
        self.knowledge_times.add(str(known_at))
        if not self.first_observed_at or observed_at < self.first_observed_at:
            self.first_observed_at = observed_at
        if not self.last_observed_at or observed_at > self.last_observed_at:
            self.last_observed_at = observed_at

        self.observations.append({
            "observed_at": observed_at,
            "knowledge_time": str(known_at),
            "status": status,
            "evidence_ids": list(evidence),
            "execution_id": execution_id or None,
        })

    def snapshot_observations(self, *, as_of: str | datetime | None = None, known_as_of: str | datetime | None = None) -> list[dict[str, Any]]:
        from .temporal_learning import observation_visible_at
        return [
            dict(item)
            for item in self.observations
            if observation_visible_at(item, as_of=as_of, known_as_of=known_as_of)
        ]

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
            "first_observed_at": self.first_observed_at,
            "last_observed_at": self.last_observed_at,
            "knowledge_times": sorted(self.knowledge_times),
            "observations": list(self.observations),
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
