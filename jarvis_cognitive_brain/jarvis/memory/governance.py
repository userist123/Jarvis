"""Deterministic memory governance for JARVIS write proposals."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import re
from typing import Any, Iterable, Mapping, Optional


_CONFIDENCE_ORDER = {"unknown": 0.0, "low": 0.25, "medium": 0.5, "high": 0.75, "very_high": 1.0}
_AUTHORITY_ORDER = {
    "user": 1.0,
    "official": 0.95,
    "execution": 0.9,
    "experience": 0.75,
    "import": 0.55,
    "ai": 0.35,
    "inference": 0.3,
    "hypothesis": 0.2,
}


@dataclass(frozen=True)
class MemoryDecision:
    action: str
    reason: str
    duplicate_of: Optional[str] = None
    conflict_with: Optional[str] = None
    similarity: float = 0.0


class MemoryGovernance:
    """Apply the vault's write, provenance, dedupe, and conflict rules."""

    def __init__(self, duplicate_threshold: float = 0.85) -> None:
        if not 0.0 <= duplicate_threshold <= 1.0:
            raise ValueError("duplicate_threshold must be between 0 and 1")
        self.duplicate_threshold = duplicate_threshold

    @staticmethod
    def normalize_text(value: str) -> str:
        value = re.sub(r"\s+", " ", str(value or "").strip().casefold())
        return value

    @classmethod
    def fingerprint(cls, content: str) -> str:
        normalized = cls.normalize_text(content)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _metadata(note: Mapping[str, Any], key: str, default: Any = None) -> Any:
        value = note.get(key, default)
        if value not in (None, ""):
            return value
        return default

    @classmethod
    def _provenance_type(cls, note: Mapping[str, Any]) -> str:
        provenance = note.get("provenance") or {}
        return str(provenance.get("source_type") or "unknown").strip().casefold()

    @classmethod
    def authority_score(cls, note: Mapping[str, Any]) -> float:
        source_type = cls._provenance_type(note)
        confidence = str(note.get("confidence") or "unknown").casefold()
        return 0.55 * _AUTHORITY_ORDER.get(source_type, 0.0) + 0.45 * _CONFIDENCE_ORDER.get(confidence, 0.0)

    @classmethod
    def _same_scope(cls, left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        for key in ("applies_to", "version_range"):
            lval = cls._metadata(left, key)
            rval = cls._metadata(right, key)
            if lval is None or rval is None:
                if lval != rval:
                    return False
            elif cls.normalize_text(str(lval)) != cls.normalize_text(str(rval)):
                return False
        return True

    @classmethod
    def similarity(cls, left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
        return SequenceMatcher(None, cls.normalize_text(left.get("content", "")), cls.normalize_text(right.get("content", ""))).ratio()

    @classmethod
    def has_required_provenance(cls, note: Mapping[str, Any]) -> bool:
        provenance = note.get("provenance") or {}
        return bool(provenance.get("source_type") and provenance.get("source_ref"))

    def evaluate(self, candidate: Mapping[str, Any], existing: Iterable[Mapping[str, Any]] = ()) -> MemoryDecision:
        content = self.normalize_text(candidate.get("content", ""))
        if not content:
            return MemoryDecision("reject", "Memory content is empty.")
        if not self.has_required_provenance(candidate):
            return MemoryDecision("review", "Missing required provenance metadata.")

        candidate_fp = self.fingerprint(content)
        for note in existing:
            note_id = str(note.get("id") or "")
            if note_id and note_id == str(candidate.get("id") or ""):
                continue
            if note.get("lifecycle") in {"superseded", "archived"}:
                continue
            if self.fingerprint(note.get("content", "")) == candidate_fp and self._same_scope(candidate, note):
                return MemoryDecision("duplicate", "Exact normalized duplicate.", duplicate_of=note_id, similarity=1.0)

            similarity = self.similarity(candidate, note)
            if similarity < self.duplicate_threshold or not self._same_scope(candidate, note):
                continue

            if self._provenance_type(candidate) == self._provenance_type(note):
                return MemoryDecision("duplicate", "High-similarity memory within the same source/scope.", duplicate_of=note_id, similarity=similarity)

            candidate_authority = self.authority_score(candidate)
            existing_authority = self.authority_score(note)
            if abs(candidate_authority - existing_authority) > 0.15:
                stronger = note_id if existing_authority > candidate_authority else None
                if stronger:
                    return MemoryDecision("conflict", "High-similarity memory has stronger provenance/authority.", conflict_with=stronger, similarity=similarity)
            return MemoryDecision("review", "High-similarity memory requires human review.", conflict_with=note_id, similarity=similarity)

        return MemoryDecision("accept", "Memory passes deterministic governance checks.")
