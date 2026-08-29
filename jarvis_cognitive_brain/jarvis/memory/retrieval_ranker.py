"""Deterministic, policy-aware ranking for JARVIS memory retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
import re
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RetrievalScore:
    note_id: str
    relevance: float
    authority: float
    confidence: float
    freshness: float
    version_match: float
    graph_bonus: float
    final_score: float
    reason: str


def _norm(value: Any) -> str:
    text = str(value or "").casefold()
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: Any) -> set[str]:
    return set(re.findall(r"[\w.-]+", _norm(value)))


class RetrievalRanker:
    """Rank candidate memories before they are admitted to working context."""

    CONFIDENCE = {"unknown": 0.0, "low": 0.25, "medium": 0.5, "high": 0.75, "very_high": 1.0}
    AUTHORITY = {
        "user": 1.0,
        "official": 0.95,
        "execution": 0.90,
        "experience": 0.75,
        "import": 0.60,
        "ai": 0.45,
        "inference": 0.35,
        "hypothesis": 0.20,
    }

    def __init__(self, *, version_bonus: float = 0.30, version_penalty: float = 0.30, max_graph_bonus: float = 0.12) -> None:
        self.version_bonus = version_bonus
        self.version_penalty = version_penalty
        self.max_graph_bonus = max(0.0, max_graph_bonus)

    @classmethod
    def lexical_relevance(cls, query: str, content: str) -> float:
        q = _tokens(query)
        c = _tokens(content)
        if not q or not c:
            return 0.0
        return len(q & c) / len(q)

    @classmethod
    def confidence_score(cls, note: Mapping[str, Any]) -> float:
        return cls.CONFIDENCE.get(_norm(note.get("confidence")), 0.0)

    @classmethod
    def authority_score(cls, note: Mapping[str, Any]) -> float:
        provenance = note.get("provenance") or {}
        return cls.AUTHORITY.get(_norm(provenance.get("source_type")), 0.20)

    @staticmethod
    def freshness_score(note: Mapping[str, Any], today: date | None = None) -> float:
        today = today or date.today()
        raw = note.get("updated") or note.get("created")
        if not raw:
            return 0.5
        try:
            parsed = date.fromisoformat(str(raw)[:10])
        except ValueError:
            return 0.5
        age_days = max(0, (today - parsed).days)
        return math.exp(-age_days / 365.0)

    @classmethod
    def version_score(cls, query: str, note: Mapping[str, Any], *, bonus: float, penalty: float) -> float:
        query_text = _norm(query)
        note_version = _norm(note.get("version_range"))
        if not note_version:
            return 0.0
        if note_version in query_text or any(part in query_text for part in note_version.split() if len(part) > 2):
            return bonus
        versionish = re.findall(r"\b(?:python|powershell|node|nodejs|dotnet|\.net|windows)\s*\d+(?:\.\d+)?(?:\.x)?\b", query_text)
        if versionish and not any(v in note_version for v in versionish):
            return -penalty
        return 0.0

    def score(self, query: str, note: Mapping[str, Any]) -> RetrievalScore:
        relevance = min(1.0, self.lexical_relevance(query, note.get("content", "")))
        authority = self.authority_score(note)
        confidence = self.confidence_score(note)
        freshness = self.freshness_score(note)
        version_match = self.version_score(query, note, bonus=self.version_bonus, penalty=self.version_penalty)
        graph_bonus = min(self.max_graph_bonus, max(0.0, float(note.get("graph_bonus", 0.0) or 0.0)))

        final = (
            (0.45 * relevance)
            + (0.20 * confidence)
            + (0.15 * authority)
            + (0.10 * freshness)
            + version_match
            + graph_bonus
        )
        lifecycle = _norm(note.get("lifecycle"))
        verification = _norm(note.get("verification"))
        if lifecycle in {"superseded", "archived"}:
            final -= 0.50
        if verification in {"unverified", "inferred"}:
            final -= 0.10

        reasons = [
            f"relevance={relevance:.2f}",
            f"confidence={confidence:.2f}",
            f"authority={authority:.2f}",
            f"freshness={freshness:.2f}",
        ]
        if version_match:
            reasons.append(f"version_adjustment={version_match:+.2f}")
        if graph_bonus:
            reasons.append(f"graph_bonus={graph_bonus:+.2f}")
        return RetrievalScore(
            note_id=str(note.get("id") or ""),
            relevance=relevance,
            authority=authority,
            confidence=confidence,
            freshness=freshness,
            version_match=version_match,
            graph_bonus=graph_bonus,
            final_score=final,
            reason=", ".join(reasons),
        )

    def rank(self, query: str, notes: Sequence[Mapping[str, Any]], *, limit: int = 10) -> list[tuple[Mapping[str, Any], RetrievalScore]]:
        scored = [(note, self.score(query, note)) for note in notes]
        scored.sort(key=lambda pair: pair[1].final_score, reverse=True)
        return scored[: max(0, limit)]
