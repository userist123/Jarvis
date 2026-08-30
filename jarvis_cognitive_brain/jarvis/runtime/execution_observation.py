"""Normalized observations emitted after a JARVIS execution boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
import hashlib
import json

from jarvis.runtime.learning_eligibility import assess_learning_eligibility


@dataclass(frozen=True)
class ExecutionObservation:
    execution_id: str
    intent: str
    status: str
    result: Any = None
    error: str | None = None
    evidence_ids: tuple[str, ...] = ()
    observed_at: str = ""
    learning_eligible: bool = False
    learning_risk: str = "low"

    def as_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "intent": self.intent,
            "success": self.status == "success",
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "evidence_ids": list(self.evidence_ids),
            "observed_at": self.observed_at,
            "learning_eligible": self.learning_eligible,
            "learning_risk": self.learning_risk,
        }


def observation_from_turn(intent: str, result: Mapping[str, Any]) -> ExecutionObservation:
    status = str(result.get("status", "unknown"))
    execution_id = str(result.get("execution_id") or "")
    if not execution_id:
        payload = json.dumps({"intent": intent, "result": dict(result)}, sort_keys=True, default=str)
        execution_id = "exec-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    evidence = result.get("evidence_ids") or result.get("evidence") or ()
    if isinstance(evidence, (str, bytes)):
        evidence = (str(evidence),)
    observation = {
        "status": status,
        "evidence_ids": tuple(str(x) for x in evidence),
        "risky_capability": bool(result.get("risky_capability")),
    }
    eligibility = assess_learning_eligibility(observation)
    return ExecutionObservation(
        execution_id=execution_id,
        intent=intent,
        status=status,
        result=result.get("result"),
        error=str(result.get("error")) if result.get("error") is not None else None,
        evidence_ids=tuple(str(x) for x in evidence),
        observed_at=datetime.now(timezone.utc).isoformat(),
        learning_eligible=eligibility.eligible,
        learning_risk=eligibility.risk,
    )
