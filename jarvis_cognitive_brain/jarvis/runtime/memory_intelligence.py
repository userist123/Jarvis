"""Deterministic memory-intelligence signals for JARVIS governance."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping


class MemorySignalType(str):
    DUPLICATE = "DUPLICATE"
    POTENTIAL_CONTRADICTION = "POTENTIAL_CONTRADICTION"
    STALE = "STALE"
    KNOWLEDGE_GAP = "KNOWLEDGE_GAP"


@dataclass(frozen=True)
class MemorySignal:
    signal_id: str
    signal_type: str
    memory_ids: tuple[str, ...]
    severity: str
    confidence: float
    reason: str
    metadata: dict[str, Any]
    detected_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "memory_ids": list(self.memory_ids),
            "severity": self.severity,
            "confidence": self.confidence,
            "reason": self.reason,
            "metadata": dict(self.metadata),
            "detected_at": self.detected_at,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _content(item: Mapping[str, Any]) -> str:
    return " ".join(str(item.get(key, "")) for key in ("title", "summary", "content", "body")).strip()


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s:/.-]", "", text)
    return text


def _claim_key(text: str) -> str:
    normalized = _normalize(text)
    first = re.split(r"[.!?\n]", normalized, maxsplit=1)[0].strip()
    first = re.sub(r"\b\d+(?:\.\d+)?\b", "#", first)
    return first[:180]


def _signal_id(kind: str, ids: Iterable[str], extra: str = "") -> str:
    payload = "|".join(sorted(str(x) for x in ids)) + "|" + kind + "|" + extra
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def detect_duplicates(records: Iterable[Mapping[str, Any]], *, now: datetime | None = None) -> list[MemorySignal]:
    now = now or _now()
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for item in records:
        text = _normalize(_content(item))
        if text:
            buckets.setdefault(text, []).append(item)
    signals: list[MemorySignal] = []
    for text, items in buckets.items():
        ids = tuple(str(item.get("id")) for item in items if item.get("id"))
        if len(ids) < 2:
            continue
        signals.append(MemorySignal(
            signal_id=_signal_id(MemorySignalType.DUPLICATE, ids),
            signal_type=MemorySignalType.DUPLICATE,
            memory_ids=ids,
            severity="medium",
            confidence=1.0,
            reason="Exact normalized content duplicate detected.",
            metadata={"normalized_length": len(text), "count": len(ids)},
            detected_at=now.isoformat(),
        ))
    return signals


def detect_potential_contradictions(records: Iterable[Mapping[str, Any]], *, now: datetime | None = None) -> list[MemorySignal]:
    now = now or _now()
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for item in records:
        text = _content(item)
        key = _claim_key(text)
        if key:
            buckets.setdefault(key, []).append(item)
    signals: list[MemorySignal] = []
    for key, items in buckets.items():
        if len(items) < 2:
            continue
        normalized = {_normalize(_content(item)) for item in items}
        if len(normalized) <= 1:
            continue
        ids = tuple(str(item.get("id")) for item in items if item.get("id"))
        if len(ids) < 2:
            continue
        signals.append(MemorySignal(
            signal_id=_signal_id(MemorySignalType.POTENTIAL_CONTRADICTION, ids, key),
            signal_type=MemorySignalType.POTENTIAL_CONTRADICTION,
            memory_ids=ids,
            severity="high",
            confidence=0.65,
            reason="Different claims share the same conservative claim key; semantic verification is required.",
            metadata={"claim_key": key, "variants": [str(_content(item))[:240] for item in items]},
            detected_at=now.isoformat(),
        ))
    return signals


def detect_stale(records: Iterable[Mapping[str, Any]], *, max_age_days: int = 180, now: datetime | None = None) -> list[MemorySignal]:
    now = now or _now()
    cutoff = now - timedelta(days=max(1, int(max_age_days)))
    signals: list[MemorySignal] = []
    for item in records:
        updated = _parse_time(item.get("updated_at") or item.get("modified_at") or item.get("created_at"))
        if updated is None or updated >= cutoff:
            continue
        memory_id = str(item.get("id") or "")
        if not memory_id:
            continue
        age_days = max(0, int((now - updated).total_seconds() // 86400))
        signals.append(MemorySignal(
            signal_id=_signal_id(MemorySignalType.STALE, (memory_id,), str(age_days)),
            signal_type=MemorySignalType.STALE,
            memory_ids=(memory_id,),
            severity="medium",
            confidence=0.95,
            reason=f"Memory has not been updated for approximately {age_days} days.",
            metadata={"updated_at": updated.isoformat(), "age_days": age_days, "max_age_days": max_age_days},
            detected_at=now.isoformat(),
        ))
    return signals


def detect_knowledge_gap(query: str, results: Iterable[Mapping[str, Any]], *, now: datetime | None = None) -> list[MemorySignal]:
    now = now or _now()
    materialized = list(results)
    if materialized:
        return []
    normalized = _normalize(query)
    if not normalized:
        return []
    signal_id = _signal_id(MemorySignalType.KNOWLEDGE_GAP, (normalized,))
    return [MemorySignal(
        signal_id=signal_id,
        signal_type=MemorySignalType.KNOWLEDGE_GAP,
        memory_ids=(),
        severity="low",
        confidence=0.90,
        reason="No memory results were returned for the requested query.",
        metadata={"query": query},
        detected_at=now.isoformat(),
    )]


def scan(records: Iterable[Mapping[str, Any]], *, max_age_days: int = 180, now: datetime | None = None) -> list[MemorySignal]:
    now = now or _now()
    materialized = list(records)
    signals = []
    signals.extend(detect_duplicates(materialized, now=now))
    signals.extend(detect_potential_contradictions(materialized, now=now))
    signals.extend(detect_stale(materialized, max_age_days=max_age_days, now=now))
    signals.sort(key=lambda item: (-item.confidence, item.signal_type, item.signal_id))
    return signals
