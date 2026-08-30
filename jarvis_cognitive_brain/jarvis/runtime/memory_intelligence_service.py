"""Service facade for deterministic memory-intelligence analysis."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .memory_intelligence import detect_knowledge_gap, scan
from .memory_intelligence_store import MemoryIntelligenceStore


class MemoryIntelligenceService:
    """Read/analyze facade; never mutates canonical Vault memory."""

    def __init__(self, store: MemoryIntelligenceStore | None = None) -> None:
        self.store = store or MemoryIntelligenceStore()

    def scan_records(self, records: Iterable[Mapping[str, Any]], *, max_age_days: int = 180) -> list[dict[str, Any]]:
        signals = scan(list(records), max_age_days=max_age_days)
        self.store.upsert_many(signals)
        return [signal.as_dict() for signal in signals]

    def record_knowledge_gap(self, query: str, results: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        signals = detect_knowledge_gap(query, list(results))
        self.store.upsert_many(signals)
        return [signal.as_dict() for signal in signals]

    def list_signals(self, *, signal_type: str | None = None, severity: str | None = None) -> list[dict[str, Any]]:
        records = self.store.records()
        if signal_type is not None:
            records = [item for item in records if item.get("signal_type") == signal_type]
        if severity is not None:
            records = [item for item in records if item.get("severity") == severity]
        return records

    def stats(self) -> dict[str, Any]:
        records = self.store.records()
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for item in records:
            by_type[str(item.get("signal_type", "UNKNOWN"))] = by_type.get(str(item.get("signal_type", "UNKNOWN")), 0) + 1
            by_severity[str(item.get("severity", "UNKNOWN"))] = by_severity.get(str(item.get("severity", "UNKNOWN")), 0) + 1
        return {
            "total": len(records),
            "by_type": by_type,
            "by_severity": by_severity,
            "read_only": True,
        }
