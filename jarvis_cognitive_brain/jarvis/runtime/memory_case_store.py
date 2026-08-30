"""Persistent store for memory-intelligence case references."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from .memory_case_factory import MemoryCaseFactory


class MemoryCaseStore:
    """Restart-safe store keyed by source signal_id."""

    def __init__(self, path: str | Path = ".jarvis/memory_cases.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            signal_id = str(item.get("signal_id") or "")
            if signal_id:
                self._records[signal_id] = dict(item)

    def factory(self) -> MemoryCaseFactory:
        return MemoryCaseFactory(self._records)

    def create_from_signal(self, signal: Mapping[str, Any]) -> dict[str, Any]:
        factory = self.factory()
        item = factory.create_from_signal(signal)
        if str(signal.get("signal_id")) not in self._records:
            self._records[str(signal["signal_id"])] = item
            self._rewrite()
        return dict(item)

    def create_many(self, signals: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        changed = False
        factory = self.factory()
        for signal in signals:
            item = factory.create_from_signal(signal)
            signal_id = str(item["signal_id"])
            if signal_id not in self._records:
                self._records[signal_id] = item
                changed = True
            created.append(dict(item))
        if changed:
            self._rewrite()
        return created

    def records(self) -> list[dict[str, Any]]:
        return [dict(self._records[key]) for key in sorted(self._records)]

    def get_by_signal(self, signal_id: str) -> dict[str, Any] | None:
        item = self._records.get(str(signal_id))
        return dict(item) if item else None

    def _rewrite(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = "".join(json.dumps(self._records[key], ensure_ascii=False, sort_keys=True) + "\n" for key in sorted(self._records))
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self.path)
