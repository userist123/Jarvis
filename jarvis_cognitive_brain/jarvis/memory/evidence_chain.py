"""Evidence-chain construction for memory-grounded decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from jarvis.memory.retrieval_ranker import RetrievalRanker


@dataclass(frozen=True)
class EvidenceItem:
    note_id: str
    score: float
    authority: float
    confidence: float
    verification: str
    relation: str | None = None


@dataclass(frozen=True)
class EvidenceDecision:
    usable: bool
    status: str
    reason: str
    evidence: tuple[EvidenceItem, ...]
    conflicts: tuple[str, ...] = ()


class EvidenceChain:
    """Build an auditable evidence chain without asking the LLM to arbitrate metadata."""

    @staticmethod
    def _verified(note: Mapping[str, Any]) -> bool:
        return str(note.get("verification") or "").casefold() == "verified"

    def build(
        self,
        query: str,
        ranked_notes: Sequence[Mapping[str, Any]],
        conflicts: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]] = (),
    ) -> EvidenceDecision:
        usable: list[EvidenceItem] = []
        conflict_ids: list[str] = []
        for left, right in conflicts:
            for note in (left, right):
                note_id = str(note.get("id") or "")
                if note_id and note_id not in conflict_ids:
                    conflict_ids.append(note_id)

        for note in ranked_notes:
            note_id = str(note.get("id") or "")
            if not note_id or note_id in conflict_ids:
                continue
            score = RetrievalRanker().score(query, note)
            usable.append(
                EvidenceItem(
                    note_id=note_id,
                    score=score.final_score,
                    authority=score.authority,
                    confidence=score.confidence,
                    verification=str(note.get("verification") or "unknown"),
                )
            )

        usable.sort(key=lambda item: item.score, reverse=True)
        if conflict_ids and not usable:
            return EvidenceDecision(False, "conflict", "No non-conflicting evidence is available.", tuple(), tuple(conflict_ids))
        if conflict_ids:
            return EvidenceDecision(True, "partial_conflict", "Conflicting memories were excluded from the usable evidence chain.", tuple(usable), tuple(conflict_ids))
        if not usable:
            return EvidenceDecision(False, "insufficient", "No usable evidence was retrieved.", tuple())

        verified = [item for item in usable if item.verification == "verified"]
        if verified:
            return EvidenceDecision(True, "verified", "At least one verified evidence item is available.", tuple(usable))
        return EvidenceDecision(True, "unverified", "Evidence exists but none is verified.", tuple(usable))
