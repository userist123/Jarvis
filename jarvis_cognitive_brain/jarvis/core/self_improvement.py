"""Controlled self-improvement candidates.

Candidates are proposals for reusable learning, never canonical truth. They remain
in REVIEW until evidence is verified and an authorized reviewer approves promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Iterable


@dataclass(frozen=True)
class LearningCandidate:
    candidate_id: str
    lesson: str
    memory_id: str
    evidence_ids: tuple[str, ...]
    risk: str
    lifecycle: str = "REVIEW"
    verification: str = "unverified"
    promotion_ready: bool = False
    created_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "lesson": self.lesson,
            "memory_id": self.memory_id,
            "evidence_ids": list(self.evidence_ids),
            "risk": self.risk,
            "lifecycle": self.lifecycle,
            "verification": self.verification,
            "promotion_ready": self.promotion_ready,
            "created_at": self.created_at,
        }


class SelfImprovementWorkflow:
    """Turn reflections into deterministic, review-gated learning candidates."""

    @staticmethod
    def _memory_id(lesson: str, evidence_ids: Iterable[str]) -> str:
        payload = json.dumps(
            {"lesson": lesson.strip(), "evidence_ids": sorted(str(x) for x in evidence_ids)},
            sort_keys=True,
            separators=(",", ":"),
        )
        return "learn-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _risk(success: bool, evidence_ids: tuple[str, ...]) -> str:
        if not success:
            return "medium" if evidence_ids else "high"
        return "low" if evidence_ids else "medium"

    def create_candidate(
        self,
        *,
        lesson: str,
        success: bool,
        evidence_ids: Iterable[str] = (),
    ) -> LearningCandidate:
        cleaned = lesson.strip()
        if not cleaned:
            raise ValueError("Learning candidate requires a non-empty lesson")
        ids = tuple(sorted({str(x) for x in evidence_ids if x}))
        memory_id = self._memory_id(cleaned, ids)
        return LearningCandidate(
            candidate_id="LC-" + memory_id[6:],
            lesson=cleaned,
            memory_id=memory_id,
            evidence_ids=ids,
            risk=self._risk(success, ids),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def mark_verified(candidate: LearningCandidate, *, evidence_valid: bool) -> LearningCandidate:
        if not evidence_valid:
            return candidate
        return LearningCandidate(
            candidate_id=candidate.candidate_id,
            lesson=candidate.lesson,
            memory_id=candidate.memory_id,
            evidence_ids=candidate.evidence_ids,
            risk=candidate.risk,
            lifecycle=candidate.lifecycle,
            verification="verified",
            promotion_ready=True,
            created_at=candidate.created_at,
        )
