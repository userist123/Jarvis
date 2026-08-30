"""Service facade for intelligence-signal case materialization."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .case_materializer import CaseMaterializer
from .memory_case_store import MemoryCaseStore


class CaseMaterializationService:
    """Materialize triaged signals without mutating canonical memory."""

    def __init__(self, case_store: MemoryCaseStore | None = None, conflict_service: Any | None = None) -> None:
        self.case_store = case_store or MemoryCaseStore()
        self.materializer = CaseMaterializer(self.case_store, conflict_service=conflict_service)

    def materialize_signal(self, signal: Mapping[str, Any]) -> dict[str, Any]:
        return self.materializer.materialize(signal).as_dict()

    def materialize_many(self, signals: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [self.materialize_signal(signal) for signal in signals]

    def list_cases(self) -> list[dict[str, Any]]:
        return self.case_store.records()
