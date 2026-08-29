"""Deterministic governance helpers for the canonical AI Memory Vault contract."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


DEFAULT_DUPLICATE_THRESHOLD = 0.85


@dataclass(frozen=True)
class MemoryCandidateDecision:
    """Outcome of validating a proposed memory against existing notes."""

    action: str
    reason: str
    similarity: float = 0.0
    matched_id: str | None = None


class MemoryGovernance:
    """Apply deterministic memory-integrity rules before persistence."""

    SOURCE_AUTHORITY = {
        "user": 1.00,
        "official": 0.95,
        "execution": 0.90,
        "experience": 0.75,
        "import": 0.60,
        "ai": 0.45,
        "inference": 0.35,
    }

    def __init__(self, duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD) -> None:
        if not 0.0 <= duplicate_threshold <= 1.0:
            raise ValueError("duplicate_threshold must be between 0 and 1")
        self.duplicate_threshold = duplicate_threshold

    @staticmethod
    def normalize_text(value: Any) -> str:
        text = str(value or "").casefold()
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def fingerprint(cls, text: Any) -> str:
        normalized = cls.normalize_text(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def token_similarity(cls, left: Any, right: Any) -> float:
        a = set(cls.normalize_text(left).split())
        b = set(cls.normalize_text(right).split())
        if not a or not b:
            return 1.0 if a == b else 0.0
        return len(a & b) / len(a | b)

    @classmethod
    def authority_score(cls, source_type: str | None) -> float:
        return cls.SOURCE_AUTHORITY.get(str(source_type or "").casefold(), 0.20)

    @classmethod
    def provenance_valid(cls, provenance: Any) -> bool:
        if not isinstance(provenance, Mapping):
            return False
        source_type = str(provenance.get("source_type") or "").strip()
        source_ref = str(provenance.get("source_ref") or "").strip()
        return bool(source_type and source_ref)

    @classmethod
    def compatible_scope(cls, candidate: Mapping[str, Any], existing: Mapping[str, Any]) -> bool:
        """Unknown technology/version scope never causes a duplicate match."""
        applies_a = candidate.get("applies_to")
        applies_b = existing.get("applies_to")
        version_a = candidate.get("version_range")
        version_b = existing.get("version_range")

        if applies_a is None or applies_b is None or version_a is None or version_b is None:
            return False
        return cls.normalize_text(applies_a) == cls.normalize_text(applies_b) and cls.normalize_text(version_a) == cls.normalize_text(version_b)

    def inspect_candidate(
        self,
        candidate: Mapping[str, Any],
        existing_notes: Sequence[Mapping[str, Any]],
    ) -> MemoryCandidateDecision:
        if not str(candidate.get("content") or "").strip():
            return MemoryCandidateDecision("reject", "Memory content is empty.")
        if not self.provenance_valid(candidate.get("provenance")):
            return MemoryCandidateDecision("review", "Provenance is incomplete.")

        candidate_content = candidate.get("content", "")
        for existing in existing_notes:
            if not existing.get("id") or existing.get("id") == candidate.get("id"):
                continue
            if not self.compatible_scope(candidate, existing):
                continue
            similarity = self.token_similarity(candidate_content, existing.get("content", ""))
            if similarity >= self.duplicate_threshold:
                return MemoryCandidateDecision(
                    "update",
                    "Existing memory is substantially equivalent within the same technology/version scope.",
                    similarity=similarity,
                    matched_id=str(existing["id"]),
                )

        verification = str(candidate.get("verification") or "unverified").casefold()
        lifecycle = str(candidate.get("lifecycle") or "REVIEW").casefold()
        if verification != "verified" or lifecycle not in {"active", "review"}:
            return MemoryCandidateDecision("review", "Candidate requires review before canonical activation.")
        return MemoryCandidateDecision("create", "Candidate satisfies deterministic governance checks.")

    @staticmethod
    def conflict(candidate: Mapping[str, Any], existing: Mapping[str, Any]) -> bool:
        """Detect a likely contradiction without silently selecting a winner."""
        if not MemoryGovernance.compatible_scope(candidate, existing):
            return False
        left = MemoryGovernance.normalize_text(candidate.get("content", ""))
        right = MemoryGovernance.normalize_text(existing.get("content", ""))
        if left == right or not left or not right:
            return False
        disjoint = len(set(left.split()) & set(right.split())) == 0
        if disjoint:
            return False
        candidate_authority = MemoryGovernance.authority_score(
            (candidate.get("provenance") or {}).get("source_type") if isinstance(candidate.get("provenance"), Mapping) else None
        )
        existing_authority = MemoryGovernance.authority_score(
            (existing.get("provenance") or {}).get("source_type") if isinstance(existing.get("provenance"), Mapping) else None
        )
        return candidate_authority != existing_authority and MemoryGovernance.token_similarity(left, right) < 0.60
