from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping


@dataclass(frozen=True)
class ReflectionResult:
    success: bool
    lesson: str
    evidence_ids: tuple[str, ...] = ()
    memory_type: str = "lesson"
    lifecycle: str = "REVIEW"
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_ids"] = list(self.evidence_ids)
        return data


class ReflectionEngine:
    """Deterministic reflection boundary for post-action learning.

    Reflection never promotes knowledge to ACTIVE. It emits a REVIEW proposal
    carrying evidence references for MemoryGovernance/MemoryController.
    """

    def reflect(
        self,
        *,
        goal: str,
        expected: str,
        observation: Mapping[str, Any],
        evidence_ids: tuple[str, ...] = (),
    ) -> ReflectionResult:
        success = bool(observation.get("success", False))
        actual = observation.get("result")
        error = str(observation.get("error", ""))

        if success:
            lesson = f"Goal '{goal}' completed. Expected: {expected}. Observed success: {actual!r}."
            reason = "successful outcome"
        else:
            lesson = f"Goal '{goal}' did not complete. Expected: {expected}. Error: {error or actual!r}."
            reason = "failed outcome"

        return ReflectionResult(
            success=success,
            lesson=lesson,
            evidence_ids=tuple(evidence_ids),
            memory_type="lesson" if success else "error",
            lifecycle="REVIEW",
            reason=reason,
        )
