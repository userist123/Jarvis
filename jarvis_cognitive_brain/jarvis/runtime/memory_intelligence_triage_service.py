"""Service facade combining persisted memory-intelligence signals with deterministic triage."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .memory_intelligence_store import MemoryIntelligenceStore
from .memory_signal_triage import triage_signals


class MemoryIntelligenceTriageService:
    """Read-only triage facade; routes signals without creating mutations."""

    def __init__(self, store: MemoryIntelligenceStore | None = None) -> None:
        self.store = store or MemoryIntelligenceStore()

    def review(self, signals: Iterable[Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
        source = list(signals) if signals is not None else self.store.records()
        return [item.as_dict() for item in triage_signals(source)]

    def summary(self) -> dict[str, Any]:
        decisions = self.review()
        by_route: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for item in decisions:
            route = str(item.get("route", "UNKNOWN"))
            priority = str(item.get("priority", "UNKNOWN"))
            by_route[route] = by_route.get(route, 0) + 1
            by_priority[priority] = by_priority.get(priority, 0) + 1
        return {
            "total": len(decisions),
            "by_route": by_route,
            "by_priority": by_priority,
            "read_only": True,
        }
