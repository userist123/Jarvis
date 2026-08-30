from __future__ import annotations

from typing import Any, Mapping, Optional
import hashlib

from jarvis.core.reflection_engine import ReflectionEngine, ReflectionResult
from jarvis.core.self_improvement import LearningCandidate, SelfImprovementWorkflow
from jarvis.memory.vault_bridge import VaultBridge
from jarvis.runtime.learning_trigger import LearningTrigger
from jarvis.runtime.learning_confidence import assess_learning_confidence
from jarvis.runtime.learning_store import PersistentLearningStore


class LearningLoop:
    """Post-action learning loop with explicit REVIEW-only persistence."""

    def __init__(
        self,
        vault_bridge: VaultBridge,
        reflection: Optional[ReflectionEngine] = None,
        *,
        store: Optional[PersistentLearningStore] = None,
        store_path: Optional[str] = None,
    ) -> None:
        self.vault = vault_bridge
        self.reflection = reflection or ReflectionEngine()
        self.self_improvement = SelfImprovementWorkflow()
        self.learning_trigger = LearningTrigger()
        self.last_candidate: Optional[LearningCandidate] = None
        self.last_learning_case: Any = None
        self.last_confidence: Any = None
        self.store = store or PersistentLearningStore(store_path or ".jarvis/learning_cases.json")

    @staticmethod
    def _proposal_id(goal: str, lesson: str, evidence_ids: tuple[str, ...]) -> str:
        payload = "|".join((goal.strip(), lesson.strip(), *sorted(evidence_ids)))
        return "lrn-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def build_candidate(self, result: ReflectionResult) -> LearningCandidate:
        candidate = self.self_improvement.create_candidate(
            lesson=result.lesson,
            success=result.success,
            evidence_ids=result.evidence_ids,
        )
        self.last_candidate = candidate
        return candidate

    def learn(
        self,
        *,
        goal: str,
        expected: str,
        observation: Mapping[str, Any],
        evidence_ids: tuple[str, ...] = (),
    ) -> tuple[ReflectionResult, Any]:
        result = self.reflection.reflect(
            goal=goal,
            expected=expected,
            observation=observation,
            evidence_ids=evidence_ids,
        )
        candidate = self.build_candidate(result)
        learning_case = self.learning_trigger.observe(
            goal=goal,
            lesson=result.lesson,
            observation={**dict(observation), "evidence_ids": list(result.evidence_ids)},
        )
        self.last_learning_case = learning_case

        if learning_case is None:
            self.last_confidence = None
            return result, None

        self.store.upsert(learning_case)
        confidence = assess_learning_confidence(learning_case)
        self.last_confidence = confidence

        proposal = {
            "id": self._proposal_id(goal, result.lesson, tuple(result.evidence_ids)),
            "title": f"JARVIS {'lesson' if result.success else 'error'}: {goal}",
            "content": result.lesson,
            "type": result.memory_type,
            "category": "learning",
            "lifecycle": "REVIEW",
            "verification": "unverified",
            "provenance": {
                "source_type": "ai",
                "source_ref": "jarvis.reflection_engine",
                "evidence_ids": sorted(set(result.evidence_ids) | learning_case.evidence_ids),
                "candidate_id": candidate.candidate_id,
                "learning_case_id": learning_case.case_id,
                "occurrences": learning_case.occurrences,
                "risk": learning_case.risk,
                "confidence": confidence.as_dict(),
            },
        }
        persisted = self.vault.propose_memory(proposal)
        return result, persisted
