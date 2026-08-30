"""Reproducible confidence snapshots for temporal learning promotion."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from .learning_confidence import LearningConfidence
from .learning_dedup import LearningCase
from .temporal_confidence import assess_temporal_confidence


@dataclass(frozen=True)
class ConfidenceSnapshot:
    case_id: str
    as_of: str | None
    known_as_of: str | None
    evidence_ids: tuple[str, ...]
    confidence: LearningConfidence
    fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "as_of": self.as_of,
            "known_as_of": self.known_as_of,
            "evidence_ids": list(self.evidence_ids),
            "confidence": self.confidence.as_dict(),
            "fingerprint": self.fingerprint,
        }


def _fingerprint(case: LearningCase, confidence: LearningConfidence, *, as_of: str | None, known_as_of: str | None) -> str:
    payload = {
        "case_id": case.case_id,
        "as_of": as_of,
        "known_as_of": known_as_of,
        "evidence_ids": sorted(case.evidence_ids),
        "outcome_counts": dict(sorted(case.outcome_counts.items())),
        "confidence": confidence.as_dict(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def build_confidence_snapshot(
    case: LearningCase,
    *,
    as_of: str | None = None,
    known_as_of: str | None = None,
) -> ConfidenceSnapshot:
    confidence = assess_temporal_confidence(case, as_of=as_of, known_as_of=known_as_of)
    fingerprint = _fingerprint(case, confidence, as_of=as_of, known_as_of=known_as_of)
    return ConfidenceSnapshot(
        case_id=case.case_id,
        as_of=as_of,
        known_as_of=known_as_of,
        evidence_ids=tuple(sorted(case.evidence_ids)),
        confidence=confidence,
        fingerprint=fingerprint,
    )


def verify_confidence_snapshot(snapshot: Mapping[str, Any], case: LearningCase) -> bool:
    expected = build_confidence_snapshot(
        case,
        as_of=snapshot.get("as_of"),
        known_as_of=snapshot.get("known_as_of"),
    )
    return (
        str(snapshot.get("case_id")) == expected.case_id
        and str(snapshot.get("fingerprint")) == expected.fingerprint
        and list(snapshot.get("evidence_ids", [])) == list(expected.evidence_ids)
        and bool((snapshot.get("confidence") or {}).get("promotable")) == expected.confidence.promotable
        and abs(float((snapshot.get("confidence") or {}).get("score", -1.0)) - expected.confidence.score) < 1e-9
    )
