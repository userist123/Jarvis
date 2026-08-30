"""Persistent store for deterministic memory-intelligence signals."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from .memory_intelligence import MemorySignal


class MemoryIntelligenceStore:
    """Append/update store keyed by stable signal_id; safe to rebuild."""

    def __init__(self, path: str | Path = ".jarvis/memory_intelligence.jsonl") -> None:
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

    def upsert(self, signal: MemorySignal) -> dict[str, Any]:
        item = signal.as_dict()
        self._records[signal.signal_id] = item
        self._rewrite()
        return dict(item)

    def upsert_many(self, signals: Iterable[MemorySignal]) -> int:
        changed = 0
        for signal in signals:
            item = signal.as_dict()
            previous = self._records.get(signal.signal_id)
            if previous != item:
                self._records[signal.signal_id] = item
                changed += 1
        if changed:
            self._rewrite()
        return changed

    def records(self) -> list[dict[str, Any]]:
        return [dict(self._records[key]) for key in sorted(self._records)]

    def get(self, signal_id: str) -> dict[str, Any] | None:
        item = self._records.get(signal_id)
        return dict(item) if item else None

    def _rewrite(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = "".join(json.dumps(self._records[key], ensure_ascii=False, sort_keys=True) + "\n" for key in sorted(self._records))
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self.path)
